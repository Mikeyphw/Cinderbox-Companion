#!/usr/bin/env python3
"""M24 read-only exact-CI-APK installed-pair attestation and Cinderbox visibility.

Requires `gh` authenticated to GitHub and an explicitly chosen ADB serial.
Downloads only the two build artifacts. No installs, root, game writes, or Steam calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable

REPO = "Mikeyphw/Cinderbox-Companion"
PACKAGES = {"app": "com.sdvsync", "test": "com.sdvsync.test"}
ARTIFACTS = {"app": "debug-apk", "test": "m14-androidtest-apk"}
CINDERBOX_PATHS = {
    "game": "/storage/emulated/0/StardewValley/desktop/GameFiles",
    "smapi": "/storage/emulated/0/StardewValley/smapi-internal",
    "legacy_game": "/storage/emulated/0/StardewValley/GameFiles",
}
EXPECTED_BRANCH = "feature/m24-steam-download-safety"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SERIAL = re.compile(r"^[a-zA-Z0-9_.:-]{1,128}$")

class ProofError(Exception):
    pass


def execute(argv: list[str], *, timeout: int = 120, runner: Callable = subprocess.run):
    try:
        return runner(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProofError("EXECUTION_UNAVAILABLE") from exc


def require_ci_identity(payload: dict, run_id: int, sha: str) -> None:
    if (payload.get("id") != run_id or payload.get("head_sha") != sha):
        raise ProofError("CI_RUN_SOURCE_MISMATCH")
    if (payload.get("status") != "completed" or payload.get("conclusion") != "success"):
        raise ProofError("CI_RUN_NOT_SUCCESSFUL")
    if (payload.get("head_branch") != EXPECTED_BRANCH or payload.get("repository", {}).get("full_name") != REPO):
        raise ProofError("CI_RUN_REPOSITORY_OR_BRANCH_MISMATCH")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def only_apk(folder: Path) -> Path:
    matches = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".apk" and not p.is_symlink()]
    if len(matches) != 1:
        raise ProofError("ARTIFACT_APK_COUNT_NOT_ONE")
    root = folder.resolve()
    path = matches[0].resolve()
    if root not in path.parents:
        raise ProofError("ARTIFACT_PATH_ESCAPE")
    return path


def parse_pm_path(output: str) -> str:
    paths = [line[len("package:"):].strip() for line in output.splitlines() if line.startswith("package:")]
    if len(paths) != 1:
        raise ProofError("INSTALLED_PACKAGE_SPLIT_OR_MISSING")
    apk = paths[0]
    if not apk.startswith("/data/app/") or not apk.endswith("/base.apk") or "\n" in apk or "\r" in apk:
        raise ProofError("INSTALLED_APK_PATH_UNEXPECTED")
    if not re.fullmatch(r"/[A-Za-z0-9_+./=~:@-]+", apk) or "/../" in apk:
        raise ProofError("INSTALLED_APK_PATH_UNSAFE")
    return apk


def parse_sha256sum(output: str, expected_path: str) -> str:
    # Fail closed on multiple lines or unexpected files/ambiguous shell output.
    match = re.fullmatch(r"([0-9a-fA-F]{64})[ \t]+\*?" + re.escape(expected_path) + r"\s*", output)
    if match is None:
        raise ProofError("DEVICE_APK_SHA256_UNAVAILABLE")
    return match.group(1).lower()


def build_receipt(run_id: int, sha: str, serial: str) -> dict:
    return dict(
        schema_version=1, producer="cinderbox-m24-installed-ci-pair-real-substrate",
        ci_run_id=run_id, ci_commit=sha, adb_serial=serial,
        overall="FAILED_OR_BLOCKED", failure_code=None,
        installed_source_verified=False, app_apk_sha256=None, test_apk_sha256=None,
        imported_cinderbox_inspected=False, cinderbox_paths={},
        installed_cinderbox_package_observed=False,
        signed_depot_manifest_verified=False, steam_entitlement_verified=False,
        authenticated_steam_tested=False, real_download_performed=False,
        game_files_modified=False, automatic_install=False, automatic_data_clear=False,
        automatic_reboot=False, root_used=False, historical_device_results_replaced=False,
        device_qualified=False, release_qualified=False, publication_allowed=False,
    )


def inspect(gh: Callable, adb: Callable, run_id: int, expected_sha: str, serial: str) -> dict:
    receipt = build_receipt(run_id, expected_sha, serial)
    result = gh(["gh", "api", f"repos/{REPO}/actions/runs/{run_id}"])
    if result.returncode:
        raise ProofError("GITHUB_RUN_LOOKUP_FAILED")
    try:
        require_ci_identity(json.loads(result.stdout), run_id, expected_sha)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProofError("CI_RUN_METADATA_INVALID") from exc

    devices = adb(["adb", "devices"])
    if devices.returncode or not any(
        len(t := line.split()) == 2 and t[0] == serial and t[1] == "device"
        for line in devices.stdout.splitlines()[1:]
    ):
        raise ProofError("EXPLICIT_ADB_DEVICE_UNAVAILABLE")

    with tempfile.TemporaryDirectory(prefix="cinderbox-m24-ci-proof-") as tmp:
        root = Path(tmp)
        for key, artifact in ARTIFACTS.items():
            folder = root / key
            folder.mkdir()
            result = gh(["gh", "run", "download", str(run_id), "--repo", REPO,
                         "--name", artifact, "--dir", str(folder)])
            if result.returncode:
                raise ProofError("GITHUB_APK_ARTIFACT_UNAVAILABLE")
            artifact_sha = sha256_file(only_apk(folder))
            package = PACKAGES[key]
            pm = adb(["adb", "-s", serial, "shell", "pm", "path", package])
            if pm.returncode:
                raise ProofError("INSTALLED_PACKAGE_UNAVAILABLE")
            remote_path = parse_pm_path(pm.stdout)
            digest = adb(["adb", "-s", serial, "shell", "sha256sum", remote_path])
            if digest.returncode:
                raise ProofError("DEVICE_APK_SHA256_UNAVAILABLE")
            installed_sha = parse_sha256sum(digest.stdout, remote_path)
            if installed_sha != artifact_sha:
                raise ProofError("INSTALLED_APK_BYTES_DIFFER_FROM_CI")
            receipt[f"{key}_apk_sha256"] = artifact_sha

    # This is read-only VISIBILITY, not storage write authorization, file integrity
    # attestation, or a reason to launch Cinderbox.
    for key, path in CINDERBOX_PATHS.items():
        observed = adb(["adb", "-s", serial, "shell", "test", "-d", path])
        receipt["cinderbox_paths"][key] = (
            "DIRECTORY_VISIBLE" if observed.returncode == 0 else "NOT_OBSERVED_OR_INACCESSIBLE"
        )
    pkg = adb(["adb", "-s", serial, "shell", "pm", "path", "com.game.cinderbox"])
    receipt["installed_cinderbox_package_observed"] = pkg.returncode == 0 and "package:" in pkg.stdout
    receipt["imported_cinderbox_inspected"] = True
    receipt["installed_source_verified"] = True
    receipt["overall"] = "PASS_CI_INSTALLED_APK_PAIR_BYTE_MATCH_READ_ONLY"
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.ci_run_id <= 0 or SHA1.fullmatch(args.expected_commit) is None or SERIAL.fullmatch(args.serial) is None:
        parser.error("A positive run ID, exact 40-character commit and explicit safe ADB serial are required")
    report = build_receipt(args.ci_run_id, args.expected_commit, args.serial)
    try:
        report = inspect(execute, execute, args.ci_run_id, args.expected_commit, args.serial)
    except ProofError as exc:
        report["failure_code"] = str(exc)
    except Exception:
        # Never print raw CI, Android or Steam details into a user-visible receipt.
        report["failure_code"] = "UNEXPECTED_PROOF_FAILURE"
    destination = args.output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if args.output.is_symlink() or destination.is_symlink():
        print("Refusing linked report destination", file=sys.stderr)
        return 1
    destination.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["installed_source_verified"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
