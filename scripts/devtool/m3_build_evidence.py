#!/usr/bin/env python3
"""M3 debug-only build evidence. Not a release signature or SLSA attestation.

Self-reported GitHub Actions evidence MUST be cross-checked against Devtool's
independent run SHA and artifact digest; it is not a cryptographic provenance
signature and must never be interpreted as one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

EXPECTED_REPO = "Mikeyphw/Cinderbox-Companion"
EXPECTED_PACKAGE = "com.sdvsync"
# Some Android Build Tools versions separate certificate digests with colons
# or wrap a digest onto the following line. Never confuse certificate hashes
# with the separate public-key digest field.
CERT_FIELD = re.compile(
    r"(?im)^[ \t]*Signer[ \t]*#([0-9]+)[ \t]+certificate[ \t]+SHA-?256[ \t]+digest:[ \t\r\n]*"
    r"((?:[0-9a-fA-F]{2}:){31}[0-9a-fA-F]{2}|[0-9a-fA-F]{64})"
)
PACKAGE_FIELD = re.compile(r"(?m)^package:\s+name='([^']+)'\s+versionCode='([0-9]+)'\s+versionName='([^']*)'")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_APK_BYTES = 256 * 1024 * 1024
POLICY_PATH = "docs/security/M3_RELEASE_POLICY.json"


class QualificationError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_policy(root: Path) -> dict:
    policy = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    required = {
        "schema_version": 1,
        "repository": EXPECTED_REPO,
        "package_name": EXPECTED_PACKAGE,
        "ci_build_variant": "debug",
        "ci_artifact_format": "apk",
        "release_enabled": False,
        "release_signing_certificate_sha256": None,
        "release_keystore_source": None,
        "automatic_device_install": False,
        "device_qualification_complete": False,
        "publication_enabled": False,
    }
    if policy != required:
        raise QualificationError("M3 signing/publication policy was changed; explicit review required")
    return policy


def check_source(root: Path) -> None:
    validate_policy(root)
    dispatched = (root / ".github/workflows/devtool-android-build.yml").read_text()
    push = (root / ".github/workflows/build.yml").read_text()
    allowed = re.findall(r"(?m)^\s*options: \[([^\]]+)\]\s*$", dispatched)
    if allowed != ["'debug'", "'apk'"]:
        raise QualificationError("Devtool dispatch must remain debug APK only")
    if "test \"$DT_VARIANT\" = 'debug'" not in dispatched:
        raise QualificationError("Devtool build variant is not fail-closed")
    for name, body in (("dispatch", dispatched), ("push", push)):
        if not re.search(r"(?m)^permissions:\s*\n\s*contents: read\s*$", body):
            raise QualificationError(f"{name} workflow must use read-only repository permissions")
        if "m3_build_evidence.py source" not in body or "m3_build_evidence.py generate" not in body:
            raise QualificationError(f"{name} workflow omits M3 evidence generation")
        if "assembleRelease" in body or "upload-release-asset" in body or "publish_release" in body:
            raise QualificationError(f"{name} workflow contains release operation")
    manifest = (root / "app/src/main/AndroidManifest.xml").read_text()
    if 'android:usesCleartextTraffic="false"' not in manifest or 'android:allowBackup="false"' not in manifest:
        raise QualificationError("App security manifest guard failed")
    gradle = (root / "app/build.gradle.kts").read_text()
    if 'applicationId = "com.sdvsync"' not in gradle or "compileSdk = 35" not in gradle:
        raise QualificationError("Unexpected Android package or compile SDK")


def inspect_zip(apk: Path) -> None:
    if apk.is_symlink() or not apk.is_file():
        raise QualificationError("APK absent or symlink")
    if not (4096 <= apk.stat().st_size <= MAX_APK_BYTES):
        raise QualificationError("APK is empty, too small, or exceeds cap")
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if not {"AndroidManifest.xml", "classes.dex"}.issubset(names):
            raise QualificationError("APK lacks Android manifest or main dex")
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise QualificationError("APK contains duplicate or corrupt members")


def _tool(name: str) -> str:
    binary = shutil.which(name)
    if binary:
        return binary
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk:
        candidates = sorted((Path(sdk) / "build-tools").glob(f"*/{name}"), reverse=True)
        for path in candidates:
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
    raise QualificationError(f"Missing Android Build Tools executable: {name}")


def _run(args: list[str]) -> str:
    completed = subprocess.run(args, capture_output=True, text=True, timeout=60, check=False)
    if completed.returncode:
        raise QualificationError(f"Android verification command failed: {Path(args[0]).name}")
    return completed.stdout + "\n" + completed.stderr


def inspect_android(apk: Path) -> dict:
    signatures = _run([_tool("apksigner"), "verify", "--print-certs", str(apk)])
    signed = [(int(number), raw.replace(":", "").lower()) for number, raw in CERT_FIELD.findall(signatures)]
    fingerprints = {digest for _, digest in signed}
    if not signed or {number for number, _ in signed} != {1} or len(fingerprints) != 1:
        raise QualificationError("Could not establish exactly one Android APK signing identity")
    # Distinguished-name fields are not necessarily in CN-first order.
    dn = re.search(r"(?im)^[ \t]*Signer[ \t]*#1[ \t]+certificate[ \t]+DN:[ \t]*(.+)$", signatures)
    if not dn or not re.search(r"(?i)(?:^|,[ \t]*)CN=Android Debug(?:,|$)", dn.group(1).strip()):
        raise QualificationError("CI artifact is not signed with the expected debug certificate")
    try:
        package_data = _run([_tool("aapt"), "dump", "badging", str(apk)])
    except QualificationError:
        package_data = _run([_tool("aapt2"), "dump", "badging", str(apk)])
    pkg = PACKAGE_FIELD.search(package_data)
    if pkg is None or pkg.group(1) != EXPECTED_PACKAGE or int(pkg.group(2)) < 1:
        raise QualificationError("APK package metadata is missing or mismatched")
    return {"package_name": pkg.group(1), "version_code": int(pkg.group(2)),
            "version_name": pkg.group(3), "signing_certificate_sha256": next(iter(fingerprints)).lower(),
            "signature_verified": True, "debug_signed": True}


def source_sha(root: Path) -> str:
    actual = _run(["git", "-C", str(root), "rev-parse", "HEAD"]).strip().lower()
    if not SHA40.fullmatch(actual):
        raise QualificationError("Invalid local Git commit")
    return actual


def generate(root: Path, apk_dir: Path, output: Path, sha: str, repo: str, ref: str, run_id: str) -> dict:
    check_source(root)
    if repo != EXPECTED_REPO or not SHA40.fullmatch(sha) or sha != source_sha(root):
        raise QualificationError("GitHub Actions source identity mismatch")
    if not (ref.startswith("refs/heads/") or ref.startswith("refs/tags/") or re.fullmatch(r"refs/pull/[1-9][0-9]*/merge", ref)):
        raise QualificationError("Invalid source ref")
    if not run_id.isdecimal() or int(run_id) < 1:
        raise QualificationError("Invalid GitHub Actions run ID")
    if apk_dir.is_symlink() or not apk_dir.is_dir():
        raise QualificationError("Invalid APK directory")
    apks = sorted(apk_dir.glob("*.apk"))
    if len(apks) != 1:
        raise QualificationError("Expected exactly one debug APK")
    apk = apks[0]
    inspect_zip(apk)
    manifest = {
        "schema_version": 1, "evidence_kind": "ci-build-self-report",
        "repository": repo, "source_commit": sha, "source_ref": ref,
        "github_run_id": run_id, "variant": "debug", "format": "apk",
        "qualified_release": False, "publication_allowed": False,
        "reproducibility_proven": False, "device_qualified": False,
        "apk": {"filename": apk.name, "size_bytes": apk.stat().st_size,
                "sha256": sha256(apk), **inspect_android(apk)}
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".m3-", dir=output.parent, delete=False) as temp:
        temp.write(data)
        tmp = Path(temp.name)
    os.replace(tmp, output)
    return manifest


def verify(apk: Path, evidence: Path, expected_sha: str = "") -> dict:
    doc = json.loads(evidence.read_text(encoding="utf-8"))
    if doc.get("schema_version") != 1 or doc.get("evidence_kind") != "ci-build-self-report":
        raise QualificationError("Unsupported evidence schema")
    if doc.get("repository") != EXPECTED_REPO or not SHA40.fullmatch(doc.get("source_commit", "")):
        raise QualificationError("Invalid evidence source identity")
    if not SHA40.fullmatch(expected_sha):
        raise QualificationError("A trusted 40-character source SHA is required to verify evidence")
    if doc["source_commit"] != expected_sha:
        raise QualificationError("Evidence source commit differs from the trusted run")
    for key in ("qualified_release", "publication_allowed", "reproducibility_proven", "device_qualified"):
        if doc.get(key) is not False:
            raise QualificationError(f"Unsupported qualification claim: {key}")
    if doc.get("variant") != "debug" or doc.get("format") != "apk":
        raise QualificationError("Not debug APK evidence")
    info = doc.get("apk")
    if not isinstance(info, dict) or not SHA64.fullmatch(info.get("sha256", "")):
        raise QualificationError("Missing artifact SHA-256")
    inspect_zip(apk)
    if apk.name != info.get("filename") or apk.stat().st_size != info.get("size_bytes") or sha256(apk) != info["sha256"]:
        raise QualificationError("APK artifact does not match its recorded hash and size")
    verified = inspect_android(apk)
    for key, value in verified.items():
        if info.get(key) != value:
            raise QualificationError(f"Evidence APK identity mismatch: {key}")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("source", "generate", "verify", "release"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--apk-dir", type=Path)
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-sha", default=os.getenv("GITHUB_SHA", ""))
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--ref", default=os.getenv("GITHUB_REF", ""))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    args = parser.parse_args(argv)
    try:
        if args.action == "release":
            validate_policy(args.root)
            raise QualificationError("Release signing and device qualification are not configured; release is blocked")
        if args.action == "source":
            check_source(args.root)
            print("M3 CI source and release-blocking policy: PASS (debug-only)")
        if args.action == "generate":
            if not args.apk_dir or not args.output:
                raise QualificationError("generate requires --apk-dir and --output")
            doc = generate(args.root, args.apk_dir, args.output, args.source_sha,
                           args.repository, args.ref, args.run_id)
            print(f"M3 debug evidence generated: {args.output}, SHA256={doc['apk']['sha256']}")
        if args.action == "verify":
            if not args.apk or not args.evidence:
                raise QualificationError("verify requires --apk and --evidence")
            doc = verify(args.apk, args.evidence, args.source_sha)
            print(f"M3 debug evidence verified for {doc['source_commit']}")
    except (QualificationError, OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f"M3 QUALIFICATION FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
