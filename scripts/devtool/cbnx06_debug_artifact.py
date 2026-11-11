#!/usr/bin/env python3
"""Package the single Gradle debug APK, with a source-bound hash receipt.

No signing/installing; this script runs solely in the hosted CI build workspace.
The APK input comes from Gradle output-metadata.json, never a guessed filename.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}\Z")
MAX_APK = 1_073_741_824

class Refused(Exception):
    pass

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def safe_regular(path: Path, label: str, limit: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise Refused(label + "_NOT_REGULAR")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= limit:
        raise Refused(label + "_UNSAFE_SIZE")

def pack(debug_dir: Path, out_dir: Path, source_sha: str) -> dict:
    if not HEX40.fullmatch(source_sha):
        raise Refused("SOURCE_SHA_INVALID")
    if debug_dir.is_symlink() or not debug_dir.is_dir():
        raise Refused("DEBUG_APK_DIRECTORY_UNAVAILABLE")
    metadata_path = debug_dir / "output-metadata.json"
    safe_regular(metadata_path, "GRADLE_METADATA", 65_536)
    try:
        info = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise Refused("GRADLE_METADATA_INVALID_JSON") from exc
    if not isinstance(info, dict):
        raise Refused("GRADLE_METADATA_NOT_OBJECT")
    if info.get("applicationId") != "com.sdvsync" or info.get("variantName") != "debug":
        raise Refused("WRONG_APPLICATION_OR_VARIANT")
    kind = info.get("artifactType")
    if not isinstance(kind, dict) or kind.get("type") != "APK":
        raise Refused("WRONG_OUTPUT_ARTIFACT_TYPE")
    elements = info.get("elements")
    if not isinstance(elements, list) or len(elements) != 1:
        raise Refused("NOT_SINGLE_GRADLE_DEBUG_OUTPUT")
    item = elements[0]
    if not isinstance(item, dict) or item.get("type") != "SINGLE" or item.get("filters") != []:
        raise Refused("SPLIT_OR_INVALID_DEBUG_APK")
    version = item.get("versionName")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise Refused("UNSAFE_VERSION_NAME")
    filename = item.get("outputFile")
    if filename != f"CinderboxCompanion-v{version}.apk":
        raise Refused("GRADLE_OUTPUT_FILENAME_MISMATCH")
    apk = debug_dir / filename
    # Prevent misleading evidence if multiple APKs were generated in the directory.
    actual = [f for f in debug_dir.iterdir() if f.name.endswith(".apk")]
    if len(actual) != 1 or actual[0] != apk:
        raise Refused("MULTIPLE_OR_UNEXPECTED_APKS")
    safe_regular(apk, "GRADLE_APK", MAX_APK)
    if out_dir.is_symlink() or (out_dir.exists() and not out_dir.is_dir()):
        raise Refused("OUTPUT_DIRECTORY_UNSAFE")
    out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    apk_dest = out_dir / "app-debug.apk"
    sums_dest = out_dir / "SHA256SUMS"
    att_dest = out_dir / "SOURCE_ATTESTATION.json"
    if any(path.exists() or path.is_symlink() for path in (apk_dest, sums_dest, att_dest)):
        raise Refused("OUTPUT_ALREADY_EXISTS")
    expected = digest(apk)
    shutil.copyfile(apk, apk_dest)
    if digest(apk_dest) != expected:
        apk_dest.unlink(missing_ok=True)
        raise Refused("COPIED_APK_SHA256_MISMATCH")
    record = {
        "schema": "cbnx06-hosted-debug-apk-v1",
        "source_sha": source_sha,
        "apk_sha256": expected,
        "physical_arm64_qualified": False,
        "live_firefox_qualified": False,
        "live_nexus_qualified": False,
        "release_qualified": False,
    }
    try:
        sums_dest.write_text(expected + "  app-debug.apk\n", encoding="ascii")
        att_dest.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise Refused("OUTPUT_ATTESTATION_WRITE_FAILED") from exc
    print("CBNX06_HF01_GRADLE_METADATA_SINGLE_DEBUG_APK_AND_SHA256_PASS")
    return record

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        pack(args.debug_dir, args.output_dir, args.source_sha)
    except Refused as exc:
        print("CBNX06_HF01_REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
