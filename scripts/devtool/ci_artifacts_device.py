#!/usr/bin/env python3
"""Download an exact successful CI APK pair, install without data clear, and run selected Android lanes.

Run from the repository checkout. No implicit test selection, uninstall, Steam calls,
root, reboot, game writes, or release publication. Requires gh authentication + adb.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

DEFAULT_REPO = "Mikeyphw/Cinderbox-Companion"
DEFAULT_APP_PACKAGE = "com.sdvsync"
DEFAULT_TEST_PACKAGE = "com.sdvsync.test"
LANE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SERIAL = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
ARTIFACT = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")
PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+\Z")


class QualificationError(Exception):
    pass


def command(args: list[str], *, timeout: int = 240) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError(f"COMMAND_UNAVAILABLE_OR_TIMEOUT:{args[0]}") from exc
    if p.returncode:
        # Do not expose full stdout/stderr: SDK and device logs can contain account details.
        raise QualificationError(f"COMMAND_FAILED:{args[0]}:exit_{p.returncode}")
    return p.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lanes(checkout: Path) -> dict[str, Path]:
    directory = checkout / "scripts" / "devtool"
    found = {}
    if directory.is_dir() and not directory.is_symlink():
        for path in sorted(directory.glob("*_device_run.py")):
            if path.is_file() and not path.is_symlink():
                name = path.name[:-len("_device_run.py")].replace("_", "-")
                if LANE_NAME.fullmatch(name):
                    found[name] = path
    return found


def select_lanes(available: dict[str, Path], requested: list[str]) -> list[tuple[str, Path]]:
    selected = []
    for group in requested:
        for name in group.split(","):
            name = name.strip()
            if name not in available:
                raise QualificationError(f"UNKNOWN_TEST_LANE:{name}; use --list-tests")
            if all(name != item[0] for item in selected):
                selected.append((name, available[name]))
    return selected


def verified_run(run_id: int, repo: str, *, expected_sha: str | None) -> dict:
    obj = json.loads(command(["gh", "api", f"repos/{repo}/actions/runs/{run_id}"], timeout=90))
    if (obj.get("id") != run_id or obj.get("repository", {}).get("full_name") != repo
            or obj.get("status") != "completed" or obj.get("conclusion") != "success"
            or not SHA40.fullmatch(str(obj.get("head_sha", "")))):
        raise QualificationError("CI_SOURCE_OR_SUCCESS_INVALID")
    if expected_sha and obj["head_sha"] != expected_sha:
        raise QualificationError("CI_COMMIT_MISMATCH")
    return obj


def one_apk(folder: Path) -> Path:
    found = []
    for item in folder.rglob("*"):
        if item.is_symlink():
            raise QualificationError("ARTIFACT_CONTAINS_SYMLINK")
        if item.name.lower().endswith(".apk"):
            if not item.is_file() or item.stat().st_size == 0 or folder.resolve() not in item.resolve().parents:
                raise QualificationError("ARTIFACT_APK_UNSAFE")
            found.append(item)
    if len(found) != 1:
        raise QualificationError(f"ARTIFACT_APK_COUNT:{len(found)}")
    return found[0]


def download(run_id: int, repo: str, artifact: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    command(["gh", "run", "download", str(run_id), "--repo", repo,
             "--name", artifact, "--dir", str(destination)], timeout=360)
    return one_apk(destination)


def check_device(serial: str) -> None:
    targets = dict(line.split() for line in command(["adb", "devices"]).splitlines()[1:]
                   if len(line.split()) == 2)
    if targets.get(serial) != "device":
        raise QualificationError("SELECTED_DEVICE_UNAVAILABLE")


def installed_digest(serial: str, package: str) -> str:
    output = command(["adb", "-s", serial, "shell", "pm", "path", package], timeout=60)
    paths = [line[8:].strip() for line in output.splitlines() if line.startswith("package:")]
    if len(paths) != 1 or not paths[0].startswith("/data/app/") or not paths[0].endswith("/base.apk"):
        raise QualificationError(f"INSTALLED_SINGLE_BASE_APK_UNAVAILABLE:{package}")
    path = paths[0]
    if not re.fullmatch(r"/[A-Za-z0-9_+./=~:@-]+", path) or "/../" in path:
        raise QualificationError("INSTALLED_APK_PATH_UNSAFE")
    actual = command(["adb", "-s", serial, "shell", "sha256sum", path], timeout=90)
    m = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?" + re.escape(path) + r"\s*", actual)
    if not m:
        raise QualificationError("INSTALLED_APK_HASH_UNAVAILABLE")
    return m.group(1).lower()


def verify_receipt(path: Path, lane: str) -> dict:
    if not path.is_file() or path.is_symlink():
        raise QualificationError(f"TEST_RECEIPT_MISSING:{lane}")
    report = json.loads(path.read_text(encoding="utf-8"))
    cases = report.get("cases")
    count = report.get("expected_cases")
    if (not str(report.get("overall", "")).startswith("PASS_")
            or report.get("failure_code") not in (None, "")
            or not isinstance(cases, dict) or not cases
            or not isinstance(count, int) or count <= 0
            or report.get("completed") != count or len(cases) != count
            or any(result != "PASS" for result in cases.values())):
        raise QualificationError(f"TEST_LANE_NOT_PASS:{lane}")
    return {"overall": report["overall"], "cases": cases, "completed": count}


def store_json(path: Path, record: dict) -> None:
    if path.is_symlink():
        raise QualificationError("REPORT_IS_SYMLINK")
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__,
        epilog="Example: --run-id 39136540831 --serial emulator-5554 --test m24-staged --test m24")
    ap.add_argument("--run-id", type=int, help="Successful GitHub Actions run ID")
    ap.add_argument("--serial", default=os.environ.get("ADB_SERIAL"),
                    help="Explicit ADB transport (or ADB_SERIAL)")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--checkout", type=Path, default=Path.cwd())
    ap.add_argument("--expected-sha", help="Optional exact CI source commit")
    ap.add_argument("--app-artifact", default="debug-apk")
    ap.add_argument("--test-artifact", default="m14-androidtest-apk")
    ap.add_argument("--app-package", default=DEFAULT_APP_PACKAGE)
    ap.add_argument("--test-package", default=DEFAULT_TEST_PACKAGE)
    ap.add_argument("--test", action="append", default=[],
                    help="Lane name (repeatable; comma-separated names also allowed). No implicit tests")
    ap.add_argument("--list-tests", action="store_true", help="List currently available test lanes")
    ap.add_argument("--skip-install", action="store_true", help="Only check exact installed APK bytes")
    ap.add_argument("--allow-source-mismatch", action="store_true",
                    help="Explicitly allow local test harness HEAD to differ from CI source")
    ap.add_argument("--output-root", type=Path, default=Path.home() / "cinderbox-ci-device-runs")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    checkout = a.checkout.expanduser().resolve()
    available = lanes(checkout)
    if a.list_tests:
        for name in available:
            print(name)
        return 0
    if (not a.run_id or a.run_id < 1 or not a.serial or not SERIAL.fullmatch(a.serial)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repo)
            or any(not ARTIFACT.fullmatch(n) for n in (a.app_artifact, a.test_artifact))
            or any(not PACKAGE.fullmatch(n) for n in (a.app_package, a.test_package))
            or (a.expected_sha and not SHA40.fullmatch(a.expected_sha))):
        raise SystemExit("Provide --run-id, --serial and valid names (see --help)")
    chosen = select_lanes(available, a.test)
    a.output_root = a.output_root.expanduser()
    if a.output_root.is_symlink():
        raise QualificationError("OUTPUT_ROOT_IS_SYMLINK")
    a.output_root.mkdir(parents=True, exist_ok=True)
    folder = a.output_root / (f"run-{a.run_id}-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    folder.mkdir(mode=0o700, exist_ok=False)
    receipt = {"schema_version": 1, "kind": "ci-apk-selective-device-qualification",
               "ci_run_id": a.run_id, "repo": a.repo, "serial": a.serial,
               "source_sha": None, "local_checkout_commit": None,
               "test_runner_source_matches_ci": None,
               "source_mismatch_override": a.allow_source_mismatch,
               "installed_source_verified": False,
               "automatic_uninstall": False, "automatic_data_clear": False,
               "real_game_modified": False, "steam_transfer_performed": False,
               "release_qualified": False, "overall": "FAILED_OR_BLOCKED",
               "selected_lanes": [item[0] for item in chosen], "tests": {}, "failure_code": None}
    summary = folder / "summary.json"
    try:
        print("[1/4] Verify GitHub run and checkout", flush=True)
        ci = verified_run(a.run_id, a.repo, expected_sha=a.expected_sha)
        receipt["source_sha"] = ci["head_sha"]
        if chosen:
            local_sha = command(["git", "-C", str(checkout), "rev-parse", "HEAD"]).strip()
            receipt["local_checkout_commit"] = local_sha
            receipt["test_runner_source_matches_ci"] = local_sha == ci["head_sha"]
            if not receipt["test_runner_source_matches_ci"] and not a.allow_source_mismatch:
                raise QualificationError("LOCAL_TEST_SOURCE_DIFFERS_FROM_CI; use matching checkout")
        print("[2/4] Download exact app + instrumentation artifacts", flush=True)
        app = download(a.run_id, a.repo, a.app_artifact, folder / "app")
        tests = download(a.run_id, a.repo, a.test_artifact, folder / "instrumentation")
        hashes = {a.app_package: sha256(app), a.test_package: sha256(tests)}
        print("[3/4] Install without data clear, then verify installed APK bytes", flush=True)
        check_device(a.serial)
        if not a.skip_install:
            for apk in (app, tests):
                command(["adb", "-s", a.serial, "install", "-r", "-t", str(apk)], timeout=240)
        for package, expected in hashes.items():
            if installed_digest(a.serial, package) != expected:
                raise QualificationError(f"INSTALLED_APK_BYTES_DIFFER_FROM_CI:{package}")
        receipt["apk_sha256"] = hashes
        receipt["installed_source_verified"] = True
        print("[4/4] Run selected isolated test lanes", flush=True)
        for name, path in chosen:
            destination = folder / (name + ".json")
            try:
                command([sys.executable, str(path), "--execute-synthetic-tests",
                         "--serial", a.serial, "--ci-run-id", str(a.run_id),
                         "--output", str(destination)], timeout=1100)
                outcome = verify_receipt(destination, name)
                receipt["tests"][name] = outcome
                print(f"  PASS {name}: {outcome['completed']} cases", flush=True)
            except QualificationError:
                receipt["tests"][name] = {"overall": "FAILED_OR_BLOCKED",
                                             "receipt": destination.name}
                raise
        receipt["overall"] = "PASS_APK_PAIR_AND_SELECTED_TESTS" if chosen else "PASS_APK_PAIR_VERIFIED_NO_TESTS_SELECTED"
        print(f"PASS: {receipt['overall']}", flush=True)
        return 0
    except (QualificationError, ValueError, json.JSONDecodeError) as e:
        receipt["failure_code"] = str(e)[:160]
        print(f"BLOCKED: {receipt['failure_code']}", file=sys.stderr)
        return 1
    finally:
        store_json(summary, receipt)
        print(f"Receipts: {summary}", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QualificationError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
