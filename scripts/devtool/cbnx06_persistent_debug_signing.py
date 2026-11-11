#!/usr/bin/env python3
"""Fail-closed hosted-only certificate gate for persistent CI debug signing.

Refuses missing/wrong signer and records source-bound evidence. Never signs an APK,
installs on a device, or reads a private key into Python memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

EXPECTED_CERT = "48954c3e9d4f9f2acaab60d56b43f06a9b7d3e3f27df3e9c2f2f9f9e6261db16"
EXPECTED_PACKAGE = "com.sdvsync"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
KEYTOOL_SHA256 = re.compile(r"(?m)^\s*SHA256:\s*([0-9a-fA-F:]{64,95})\s*$")
APK_SIGNERS = re.compile(r"(?m)^Signer #(\d+) certificate SHA-256 digest:\s*([0-9a-fA-F]{64})\s*$")
APK_V2 = re.compile(r"(?m)^Verified using v2 scheme \(APK Signature Scheme v2\): true\s*$")
MAX_APK_BYTES = 1_073_741_824


class Refused(Exception):
    pass


def require_regular(path: Path, label: str, max_bytes: int) -> None:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= max_bytes:
        raise Refused(label + "_NOT_SAFE_REGULAR_FILE")


def run_checked(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, text=True, encoding="utf-8", errors="replace",
                                capture_output=True, env={**os.environ, "LC_ALL": "C"}, timeout=60)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise Refused("SIGNING_TOOL_FAILED") from exc
    return result.stdout


def require_cert_match(actual: str) -> str:
    if not HEX64.fullmatch(actual.lower()):
        raise Refused("SIGNER_CERT_FORMAT_INVALID")
    if actual.lower() != EXPECTED_CERT:
        raise Refused("SIGNER_CERT_DOES_NOT_MATCH_INSTALLED_CINDERBOX")
    return actual.lower()


def keytool_fingerprint(output: str) -> str:
    matches = KEYTOOL_SHA256.findall(output)
    if len(matches) != 1:
        raise Refused("KEYSTORE_CERT_NOT_UNIQUE")
    return require_cert_match(matches[0].replace(":", "").lower())


def apk_fingerprint(output: str) -> str:
    matches = APK_SIGNERS.findall(output)
    if len(matches) != 1 or matches[0][0] != "1":
        raise Refused("APK_SIGNER_COUNT_NOT_ONE")
    if not APK_V2.search(output):
        raise Refused("APK_V2_SIGNATURE_NOT_VERIFIED")
    return require_cert_match(matches[0][1].lower())


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def preflight(keystore: Path) -> None:
    if os.environ.get("CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING") != "true":
        raise Refused("PERSISTENT_SIGNING_NOT_MANDATORY")
    password = os.environ.get("CINDERBOX_DEBUG_STORE_PASSWORD", "")
    key_password = os.environ.get("CINDERBOX_DEBUG_KEY_PASSWORD", "")
    if not password or not key_password:
        raise Refused("SIGNING_PASSWORD_SECRET_MISSING")
    require_regular(keystore, "KEYSTORE", 1_048_576)
    if keystore.stat().st_mode & 0o077:
        raise Refused("KEYSTORE_PERMISSIONS_TOO_OPEN")
    # Check the *actual* key alias/certificate; fail before Gradle if it differs.
    fingerprint = keytool_fingerprint(run_checked([
        "keytool", "-list", "-v", "-storetype", "PKCS12", "-alias", "androiddebugkey",
        "-keystore", str(keystore), "-storepass", password,
    ]))
    print("CBNX06_PERSISTENT_DEBUG_KEYSTORE_CERT_PIN_PASS=" + fingerprint)


def attest(apk: Path, output_dir: Path, source_sha: str, apksigner: Path) -> dict:
    if not HEX40.fullmatch(source_sha):
        raise Refused("SOURCE_SHA_INVALID")
    if os.environ.get("CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING") != "true":
        raise Refused("PERSISTENT_SIGNING_NOT_MANDATORY")
    require_regular(apk, "APK", MAX_APK_BYTES)
    require_regular(apksigner, "APKSIGNER", 32 * 1024 * 1024)
    if output_dir.is_symlink() or not output_dir.is_dir() or apk.parent != output_dir:
        raise Refused("ARTIFACT_DIRECTORY_MISMATCH")
    original = output_dir / "SOURCE_ATTESTATION.json"
    require_regular(original, "SOURCE_ATTESTATION", 64 * 1024)
    try:
        record = json.loads(original.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise Refused("SOURCE_ATTESTATION_INVALID") from exc
    actual_apk_hash = digest(apk)
    if (record.get("source_sha") != source_sha or record.get("apk_sha256") != actual_apk_hash
            or record.get("release_qualified") is not False):
        raise Refused("SOURCE_ATTESTATION_NOT_MATCHING_APK")
    cert = apk_fingerprint(run_checked([str(apksigner), "verify", "--verbose", "--print-certs", str(apk)]))
    signed = {
        "schema": "cbnx06-persistent-debug-signer-v1",
        "source_sha": source_sha,
        "apk_sha256": actual_apk_hash,
        "application_id": EXPECTED_PACKAGE,
        "signing_config": "ciDebug",
        "certificate_sha256": cert,
        "matches_observed_installed_signer": True,
        "installed_apk_bytes_verified_equal": False,
        "physical_qualified": False,
        "release_qualified": False,
    }
    out = output_dir / "SIGNER_ATTESTATION.json"
    if out.exists() or out.is_symlink():
        raise Refused("SIGNER_ATTESTATION_ALREADY_EXISTS")
    out.write_text(json.dumps(signed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("CBNX06_PERSISTENT_DEBUG_APK_CERT_PIN_AND_SOURCE_PASS=" + cert)
    return signed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--keystore", type=Path, required=True)
    a = sub.add_parser("attest")
    a.add_argument("--apk", type=Path, required=True)
    a.add_argument("--output-dir", type=Path, required=True)
    a.add_argument("--source-sha", required=True)
    a.add_argument("--apksigner", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.phase == "preflight":
            preflight(args.keystore)
        else:
            attest(args.apk, args.output_dir, args.source_sha, args.apksigner)
    except Refused as exc:
        print("CBNX06_SIGNING_REFUSED:" + str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
