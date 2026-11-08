#!/usr/bin/env python3
"""Strict allowlist/PNG/source integrity receipt. Never handles API keys or provider bodies."""
from __future__ import annotations
import hashlib
import json
import re
import struct
import zlib
import sys
from pathlib import Path

STAGES = ('discover', 'page-two', 'detail', 'file-review', 'returned',
          'auth-401', 'rate-429', 'server-503', 'no-key')
DIMENSIONS = {360: (720, 1600), 393: (786, 1704)}


def verify(folder: Path, source_sha: str, run_id: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha):
        raise ValueError('NEX_R3_SOURCE_PIN_REFUSED')
    if not re.fullmatch(r'[0-9]{1,20}', run_id):
        raise ValueError('NEX_R3_RUN_ID_REFUSED')
    expected = {f'{stage}-{width}.png' for stage in STAGES for width in DIMENSIONS}
    found = {p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() == '.png'}
    if found != expected:
        raise ValueError('NEX_R3_SCREENSHOT_INVENTORY_REFUSED')
    captures = []
    for name in sorted(expected):
        file = folder / name
        if file.is_symlink():
            raise ValueError('NEX_R3_SCREENSHOT_SYMLINK_REFUSED')
        raw = file.read_bytes()
        if len(raw) < 4000 or len(raw) > 20_000_000 or raw[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('NEX_R3_PNG_HEADER_REFUSED')
        width = int(name.rsplit('-', 1)[-1][:-4])
        chunks = []
        position = 8
        seen_iend = False
        while position + 12 <= len(raw):
            size = struct.unpack('>I', raw[position:position + 4])[0]
            kind = raw[position + 4:position + 8]
            end = position + 12 + size
            if size > 20_000_000 or end > len(raw):
                raise ValueError('NEX_R3_PNG_TRUNCATED')
            data = raw[position + 8:position + 8 + size]
            actual_crc = struct.unpack('>I', raw[end - 4:end])[0]
            if actual_crc != (zlib.crc32(kind + data) & 0xffffffff):
                raise ValueError('NEX_R3_PNG_CRC_REFUSED')
            chunks.append((kind, data))
            position = end
            if kind == b'IEND':
                seen_iend = True
                break
        if not seen_iend or position != len(raw) or not chunks or chunks[0][0] != b'IHDR':
            raise ValueError('NEX_R3_PNG_STRUCTURE_REFUSED')
        if len(chunks[0][1]) != 13:
            raise ValueError('NEX_R3_PNG_IHDR_REFUSED')
        w, h = struct.unpack('>II', chunks[0][1][:8])
        if (w, h) != DIMENSIONS[width]:
            raise ValueError('NEX_R3_VIEWPORT_REFUSED')
        data = b''.join(value for kind, value in chunks if kind == b'IDAT')
        if not data:
            raise ValueError('NEX_R3_PNG_IDAT_MISSING')
        try:
            stream = zlib.decompressobj()
            uncompressed = stream.decompress(data, 8_000_000)
            if not uncompressed or not stream.eof:
                raise ValueError('NEX_R3_PNG_DECOMPRESSION_REFUSED')
        except zlib.error as err:
            raise ValueError('NEX_R3_PNG_DECOMPRESSION_REFUSED') from err
        captures.append({'file': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                         'width_px': w, 'height_px': h,
                         'source': 'hosted_ephemeral_emulator_synthetic_provider'})
    return {
        'schema_version': 1, 'source_sha': source_sha, 'run_id': run_id,
        'tests': '3_real_MainActivity_navigation_and_failure_instrumentation_tests_per_viewport',
        'android_api': 36, 'font_scale': 1.0,
        'real_main_activity': True, 'provider_responses_are_synthetic': True,
        'provider_transport_offline': True, 'file_review_navigation_only': True,
        'actual_downloads_or_installations_tested': False,
        'live_nexus_schema_qualified_by_this_run': False,
        'user_account_tested': False, 'physical_device_qualified': False,
        'release_qualified': False, 'golden_images_approved': False,
        'screenshots': captures,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        raise SystemExit('usage: nex_r3_evidence.py <dir> <source-sha> <run-id>')
    root = Path(argv[1]).resolve()
    receipt = verify(root, argv[2], argv[3])
    dest = root / 'NEX_R3_HOSTED_EVIDENCE.json'
    dest.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print('NEX_R3_SOURCE_BOUND_18_SCREENSHOT_INTEGRITY_PASS', len(receipt['screenshots']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
