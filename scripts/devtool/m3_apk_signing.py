#!/usr/bin/env python3
"""Extract Android APK v2/v3 signing identities, without parsing apksigner stdout.

Important: this module does NOT authenticate signatures. Call `apksigner verify`
and require exit code zero FIRST; the APK signing block is only the source of
verified certificate bytes. SHA-256 is taken from the leaf DER certificate.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct
import subprocess

APK_MAGIC = b"APK Sig Block 42"
APK_V2_ID = 0x7109871A
APK_V3_ID = 0xF05368C0
APK_V31_ID = 0x1B93AD61
MAX_BLOCK_SIZE = 16 * 1024 * 1024
MAX_ENTRY_SIZE = 8 * 1024 * 1024


class SigningBlockError(ValueError):
    pass


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise SigningBlockError("Truncated APK signing block")
    return struct.unpack_from("<I", data, offset)[0]


def _u64(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 8 > len(data):
        raise SigningBlockError("Truncated APK signing block")
    return struct.unpack_from("<Q", data, offset)[0]


def _length_prefixed(data: bytes, pos: int) -> tuple[bytes, int]:
    size = _u32(data, pos)
    pos += 4
    if size > MAX_ENTRY_SIZE or pos + size > len(data):
        raise SigningBlockError("Invalid signing-block field length")
    return data[pos:pos + size], pos + size


def _sequence(data: bytes) -> list[bytes]:
    chunks: list[bytes] = []
    pos = 0
    while pos < len(data):
        chunk, pos = _length_prefixed(data, pos)
        chunks.append(chunk)
        if len(chunks) > 64:
            raise SigningBlockError("Excessive signing-block entries")
    return chunks


def _signer_leaf(signer: bytes) -> bytes:
    signed_data, _ = _length_prefixed(signer, 0)
    # v2, v3 and v3.1 all start signed-data with digests and certificates.
    _, after_digests = _length_prefixed(signed_data, 0)
    certificates, _ = _length_prefixed(signed_data, after_digests)
    chain = _sequence(certificates)
    if not chain or not chain[0] or chain[0][0] != 0x30:
        raise SigningBlockError("No X.509 leaf certificate in APK signer")
    return chain[0]


def _signer_block(apk: Path) -> dict[int, bytes]:
    """Read the size-checked signing block immediately before the ZIP CD."""
    with apk.open("rb") as f:
        size = f.seek(0, 2)
        # Search EOCD in last 65535 comment bytes + 22-byte EOCD.
        f.seek(max(0, size - (65535 + 22)))
        tail = f.read()
        offset = tail.rfind(b"PK\x05\x06")
        if offset < 0 or offset + 22 > len(tail):
            raise SigningBlockError("APK ZIP end-of-central-directory missing")
        # ZIP comment must end at EOF; do not be fooled by an embedded marker.
        if offset + 22 + struct.unpack_from("<H", tail, offset + 20)[0] != len(tail):
            raise SigningBlockError("Invalid APK ZIP end record")
        if struct.unpack_from("<H", tail, offset + 4)[0] != 0 or struct.unpack_from("<H", tail, offset + 6)[0] != 0:
            raise SigningBlockError("Multidisk ZIP not supported")
        cd_offset = _u32(tail, offset + 16)
        if cd_offset == 0xffffffff or cd_offset > size or cd_offset < 32:
            raise SigningBlockError("Unsupported ZIP64 or invalid central directory")
        f.seek(cd_offset - 24)
        footer = f.read(24)
        if len(footer) != 24 or footer[8:] != APK_MAGIC:
            raise SigningBlockError("No APK v2/v3 signing block")
        block_size = _u64(footer, 0)
        if block_size < 24 or block_size > MAX_BLOCK_SIZE:
            raise SigningBlockError("APK signing block exceeds limits")
        start = cd_offset - (block_size + 8)
        if start < 0:
            raise SigningBlockError("Invalid APK signing-block offset")
        f.seek(start)
        block = f.read(block_size + 8)
        if len(block) != block_size + 8 or _u64(block, 0) != block_size or block[-16:] != APK_MAGIC:
            raise SigningBlockError("Inconsistent APK signing-block sizes")
    pairs: dict[int, bytes] = {}
    pos = 8
    end = len(block) - 24
    while pos < end:
        length = _u64(block, pos)
        if length < 4 or length > MAX_BLOCK_SIZE or pos + 8 + length > end:
            raise SigningBlockError("Malformed APK signing-block pair")
        ident = _u32(block, pos + 8)
        if ident in pairs:
            raise SigningBlockError("Duplicate APK signing-block identifier")
        pairs[ident] = block[pos + 12:pos + 8 + length]
        pos += 8 + length
    if pos != end:
        raise SigningBlockError("Malformed APK signing-block alignment")
    return pairs


def verified_signing_certificate(apk: Path) -> bytes:
    """Return consistent single-signer leaf DER across verified v2/v3 blocks.

    Caller MUST have run apksigner verify successfully on the same, unchanged APK.
    If multiple schemes are present, they must advertise the same certificate.
    """
    pairs = _signer_block(apk)
    leaves = []
    for ident in (APK_V2_ID, APK_V3_ID, APK_V31_ID):
        if ident not in pairs:
            continue
        signer_list, consumed = _length_prefixed(pairs[ident], 0)
        if consumed != len(pairs[ident]):
            raise SigningBlockError("Trailing APK signer data")
        signers = _sequence(signer_list)
        if len(signers) != 1:
            raise SigningBlockError("Expected exactly one APK signer")
        leaves.append(_signer_leaf(signers[0]))
    if not leaves:
        raise SigningBlockError("APK has no v2/v3 signing identity")
    hashes = {hashlib.sha256(leaf).hexdigest() for leaf in leaves}
    if len(hashes) != 1:
        raise SigningBlockError("APK signing schemes disagree on signer certificate")
    return leaves[0]


def certificate_sha256(apk: Path) -> str:
    return hashlib.sha256(verified_signing_certificate(apk)).hexdigest()


def is_android_debug_certificate(apk: Path) -> bool:
    """Identify the leaf subject without trusting locale-dependent apksigner text."""
    cert = verified_signing_certificate(apk)
    try:
        result = subprocess.run(
            ["openssl", "x509", "-inform", "DER", "-noout", "-subject", "-nameopt", "RFC2253"],
            input=cert, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    subject = result.stdout.decode("utf-8", errors="replace").strip()
    if not subject.startswith("subject="):
        return False
    subject = subject.removeprefix("subject=").strip()
    return re.search(r"(?:^|,)\s*CN=Android Debug(?:,|$)", subject, re.IGNORECASE) is not None
