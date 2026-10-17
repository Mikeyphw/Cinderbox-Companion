#!/usr/bin/env python3
"""M22: read-only, source-bound Devtool/GitHub baseline; no device or Steam IO.

Historical counts in this report are *anchors*, not original receipt imports.
Validation distinguishes source contract success from incomplete original receipts.
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
import tomllib

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path("scripts/devtool/m22_baseline_contract.json")
REQUIRED = (
    ".devtool.toml", "devtoolw", "scripts/devtool/m22_baseline.py",
    "scripts/devtool/m22_baseline_contract.json", "scripts/devtool/test_m22_baseline.py",
    "docs/security/M3_RELEASE_POLICY.json", "docs/devtool/DEVTOOL_IMPROVEMENTS.md",
    "docs/devtool/M22_POSTMERGE_BASELINE.md",
    ".github/workflows/build.yml", ".github/workflows/devtool-android-build.yml",
    "scripts/devtool/m21_campaign.py", "scripts/devtool/m21_scenarios.json",
    "app/src/androidTest/java/com/sdvsync/qualification/M21ReadinessDeviceTest.kt",
)
REPO = "Mikeyphw/Cinderbox-Companion"
SHA = re.compile(r"^[0-9a-f]{40}$")

class BaselineError(ValueError):
    """A malformed claim or unsafe input, never a qualifying result."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def safe_file(root: Path, rel: str) -> Path:
    if (not isinstance(rel, str) or not rel or Path(rel).is_absolute()
            or ".." in Path(rel).parts or "\\" in rel):
        raise BaselineError("INVALID_SOURCE_PATH")
    f = root / rel
    # Do not follow symlinks, including intermediate path components.
    cur = root
    for item in Path(rel).parts:
        cur = cur / item
        if cur.is_symlink():
            raise BaselineError("SYMLINK_SOURCE_REJECTED")
    if not f.is_file():
        raise BaselineError("SOURCE_FILE_MISSING")
    return f


def read_json(root: Path, rel: str) -> dict:
    value = json.loads(safe_file(root, rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BaselineError("INVALID_JSON_OBJECT")
    return value


def check_contract(c: dict) -> None:
    if c.get("schema_version") != 1 or c.get("repository") != REPO:
        raise BaselineError("MANIFEST_IDENTITY_INVALID")
    if not SHA.fullmatch(c.get("starting_master_commit", "")):
        raise BaselineError("BASE_COMMIT_INVALID")
    history = c.get("historical_acceptance", {})
    earlier = history.get("m14_m20", {})
    later = history.get("m21", {})
    if (type(earlier.get("observations_reported_pass")) is not int or earlier["observations_reported_pass"] != 74
            or type(later.get("observations_reported_pass")) is not int or later["observations_reported_pass"] != 18
            or later.get("lanes") != {"U": 4, "I": 6, "T": 4, "R": 4}
            or history.get("total_reported_pass_observations") != 92):
        raise BaselineError("HISTORICAL_OBSERVATION_DRIFT")
    if (earlier.get("original_receipts_in_repository") is not False
            or later.get("original_receipts_in_repository") is not False
            or earlier.get("availability") != "NOT_ATTACHED"
            or later.get("availability") != "NOT_ATTACHED"
            or history.get("receipt_index_completeness") != "HISTORICAL_REFERENCES_ONLY"):
        raise BaselineError("FALSE_ORIGINAL_RECEIPT_CLAIM")
    if later.get("original_reviewed_source") != "d93d21d2f569d947bce91099ef112e3b6a793452":
        raise BaselineError("M21_SOURCE_DRIFT")
    if (c.get("starting_master_ci", {}).get("source_commit") != c["starting_master_commit"]
            or c["starting_master_ci"].get("run_id") != 39040952179):
        raise BaselineError("BASE_CI_ANCHOR_DRIFT")
    ids = set()
    for a in c.get("historical_ci_anchors", []):
        if (type(a.get("run_id")) is not int or not SHA.fullmatch(a.get("source_commit", ""))
                or a.get("observed_conclusion") != "success" or a["run_id"] in ids):
            raise BaselineError("CI_HISTORY_INVALID")
        ids.add(a["run_id"])
    if {38979859033, 38989044246, 38964234525, 39040952179} - ids:
        raise BaselineError("CI_HISTORY_INCOMPLETE")
    for key in ("M22", "M23", "M24", "M25", "M26", "M27", "M28", "M29"):
        if key not in c.get("coverage_matrix", {}):
            raise BaselineError("ROADMAP_GAP")
    if set(c["coverage_matrix"]["M22"].get("required", [])) != {
            "master_sha_ci", "historical_receipts_index", "devtool_job_inventory", "coverage_gaps"}:
        raise BaselineError("M22_COVERAGE_GAP")
    for key in ("M23", "M24"):
        if c["coverage_matrix"][key].get("device_campaign") != "NOT_RUN":
            raise BaselineError("UNQUALIFIED_DEVICE_CLAIM")
    s = c.get("safety_contract", {})
    if (any(s.get(flag) is not False for flag in ("release_enabled", "device_qualification_complete", "publication_enabled", "automatic_device_install"))
            or s.get("real_game_mutation") != "FORBIDDEN_IN_M22"
            or s.get("steam_mutation") != "FORBIDDEN_IN_M22"):
        raise BaselineError("SAFETY_CONTRACT_WEAKENED")


def inventory_devtool(cfg: dict) -> dict:
    targets = cfg.get("targets", {})
    target = targets.get("cinderbox", {})
    jobs = target.get("jobs", {})
    flows = target.get("workflows", {})
    wrappers = cfg.get("wrapper", {}).get("commands", {})
    expected = {"security-contract", "m22-host-tests", "m22-baseline", "unit-tests", "android-lint", "debug-apk", "verify-debug-apk"}
    if not expected.issubset(jobs):
        raise BaselineError("DEVTOOL_JOB_MISSING")
    if any(j.get("runner") not in ("command", "android") for j in jobs.values()):
        raise BaselineError("UNEXPECTED_JOB_RUNNER")
    if (wrappers.get("m22-check", {}).get("workflow") != "m22-check"
            or wrappers.get("m22-full", {}).get("workflow") != "m22-full"):
        raise BaselineError("WRAPPER_CONTRACT_MISSING")
    dag = {}
    for name, nodes in flows.items():
        if not isinstance(nodes, list):
            raise BaselineError("INVALID_WORKFLOW")
        graph = {}
        for node in nodes:
            if isinstance(node, str):
                if not node.startswith("job:"):
                    raise BaselineError("INVALID_WORKFLOW_JOB")
                node_id, ref, deps = node, node, []
            elif isinstance(node, dict):
                node_id, ref, deps = node.get("id"), node.get("ref"), node.get("depends_on", [])
            else:
                raise BaselineError("INVALID_WORKFLOW_NODE")
            if (not isinstance(node_id, str) or not isinstance(ref, str)
                    or not ref.startswith("job:") or ref[4:] not in jobs
                    or not isinstance(deps, list) or any(not isinstance(d, str) for d in deps)
                    or node_id in graph):
                raise BaselineError("BAD_WORKFLOW_REFERENCE")
            graph[node_id] = deps
        seen, visiting = set(), set()
        def walk(n: str) -> None:
            if n in visiting:
                raise BaselineError("WORKFLOW_CYCLE")
            if n in seen:
                return
            if n not in graph:
                raise BaselineError("WORKFLOW_DEPENDENCY_MISSING")
            visiting.add(n)
            for dep in graph[n]:
                walk(dep)
            visiting.remove(n)
            seen.add(n)
        for n in graph:
            walk(n)
        dag[name] = {"node_count": len(graph), "dependency_edges": sum(map(len, graph.values()))}
    for n in ("m22-check", "m22-full"):
        if n not in dag:
            raise BaselineError("M22_WORKFLOW_MISSING")
    if not target.get("android", {}).get("instrumentation") == "disabled":
        raise BaselineError("UNEXPECTED_AUTO_DEVICE_INSTRUMENTATION")
    return {"target_count": len(targets), "job_count": len(jobs), "workflow_count": len(flows),
            "wrapper_command_count": len(wrappers), "workflows": dict(sorted(dag.items())),
            "m22_host_jobs": ["security-contract", "m22-host-tests", "m22-baseline"],
            "android_device_execution": "EXPLICIT_ONLY"}


def identify_source(root: Path, environ: dict) -> dict:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BaselineError("GIT_IDENTITY_UNAVAILABLE") from exc
    sha = proc.stdout.strip()
    if proc.returncode != 0 or not SHA.fullmatch(sha):
        raise BaselineError("GIT_IDENTITY_INVALID")
    gh_sha = environ.get("GITHUB_SHA", "")
    if gh_sha and (not SHA.fullmatch(gh_sha) or gh_sha != sha):
        raise BaselineError("GITHUB_SOURCE_MISMATCH")
    gh_repo = environ.get("GITHUB_REPOSITORY", "")
    if gh_repo and gh_repo != REPO:
        raise BaselineError("GITHUB_REPOSITORY_MISMATCH")
    gh_run = environ.get("GITHUB_RUN_ID", "")
    if gh_run and (not gh_run.isdecimal() or int(gh_run) <= 0):
        raise BaselineError("GITHUB_RUN_ID_INVALID")
    return {"commit": sha, "github_run_id": int(gh_run) if gh_run else None,
            "github_ref": environ.get("GITHUB_REF", "")[:100] if gh_run else None,
            "github_checkout_binding": "MATCHED" if gh_sha else "NOT_PROVIDED",
            "new_source_ci_result": "IN_PROGRESS_NOT_FINAL_VERIFIED" if gh_run else "NOT_RUN_BY_THIS_REPORT"}


def produce(root: Path = ROOT, environ: dict | None = None) -> dict:
    env = os.environ if environ is None else environ
    manifest = read_json(root, str(MANIFEST))
    check_contract(manifest)
    policy = read_json(root, "docs/security/M3_RELEASE_POLICY.json")
    for flag in ("release_enabled", "device_qualification_complete", "publication_enabled", "automatic_device_install"):
        if policy.get(flag) is not False:
            raise BaselineError("RELEASE_POLICY_NOT_DISABLED")
    if policy.get("repository") != REPO or policy.get("ci_build_variant") != "debug":
        raise BaselineError("RELEASE_POLICY_IDENTITY_CHANGED")
    source = identify_source(root, env)
    config = tomllib.loads(safe_file(root, ".devtool.toml").read_text(encoding="utf-8"))
    devtool = inventory_devtool(config)
    names = REQUIRED + tuple(manifest["m23_m24_existing_source_components"])
    file_hashes = {p: digest(safe_file(root, p).read_bytes()) for p in names}
    # Explicit provenance of the report's own implementation and frozen inputs.
    hist = manifest["historical_acceptance"]
    result = {
        "schema_version": 1, "producer": "cinderbox-m22-baseline",
        "overall": "PASS_M22_HOST_INVENTORY",
        "milestone_qualification": "INCOMPLETE_ORIGINAL_RECEIPTS_AND_NEW_CI",
        "source": source, "source_sha256": dict(sorted(file_hashes.items())),
        "starting_master": manifest["starting_master_commit"],
        "starting_master_ci": manifest["starting_master_ci"],
        "historical_observations": {
            "m14_m20_pass_reported": hist["m14_m20"]["observations_reported_pass"],
            "m21_pass_reported": hist["m21"]["observations_reported_pass"],
            "total_pass_reported": hist["total_reported_pass_observations"],
            "m21_original_source": hist["m21"]["original_reviewed_source"],
            "original_receipts": "NOT_ATTACHED",
            "reexecuted_for_m22": False,
            "new_source_device_pass_count": 0,
        },
        "historical_ci_anchors": manifest["historical_ci_anchors"],
        "devtool_inventory": devtool,
        "coverage_matrix": manifest["coverage_matrix"],
        "existing_m23_m24_components": {p: file_hashes[p] for p in manifest["m23_m24_existing_source_components"]},
        "coverage_gaps": ["ORIGINAL_DEVICE_RECEIPTS_NOT_ATTACHED", "M22_NEW_SOURCE_GITHUB_CI_NOT_FINAL_VERIFIED",
                          "M23_REAL_INSTALL_DISCOVERY_NOT_QUALIFIED", "M24_REAL_STEAM_DOWNLOAD_NOT_QUALIFIED",
                          "M27_MULTI_ACCESS_ANDROID_NOT_QUALIFIED"],
        "release_enabled": False, "device_qualification_complete": False,
        "publication_enabled": False, "release_qualified": False,
        "historical_receipts_overwritten": False,
        "game_or_steam_mutations": False,
    }
    result["receipt_sha256"] = digest(canonical(result))
    return result


def verify_report(report: dict, root: Path = ROOT, environ: dict | None = None) -> None:
    if not isinstance(report, dict) or report.get("schema_version") != 1 or report.get("overall") != "PASS_M22_HOST_INVENTORY":
        raise BaselineError("REPORT_SCHEMA_INVALID")
    provided = report.get("receipt_sha256")
    unsigned = dict(report)
    unsigned.pop("receipt_sha256", None)
    if not isinstance(provided, str) or digest(canonical(unsigned)) != provided:
        raise BaselineError("REPORT_DIGEST_MISMATCH")
    new = produce(root, environ)
    if report != new:
        raise BaselineError("REPORT_CURRENT_SOURCE_OR_CONTEXT_MISMATCH")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, help="Write sanitized machine-readable source inventory")
    p.add_argument("--verify", type=Path, help="Verify an existing report against current source and CI context")
    args = p.parse_args(argv)
    try:
        if args.verify:
            report = json.loads(args.verify.read_text(encoding="utf-8"))
            verify_report(report)
            value = {"schema_version": 1, "producer": "cinderbox-m22-baseline", "overall": "PASS_M22_REPORT_REVALIDATED",
                     "source_commit": report["source"]["commit"], "release_qualified": False, "publication_enabled": False}
        else:
            value = produce()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")
        print(json.dumps(value, sort_keys=True, indent=2))
        return 0
    except (BaselineError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as exc:
        error = {"schema_version": 1, "producer": "cinderbox-m22-baseline", "overall": "BLOCKED_M22_BASELINE",
                 "failure_code": str(exc) if isinstance(exc, BaselineError) else type(exc).__name__,
                 "release_qualified": False, "publication_enabled": False}
        # Fail closed without publishing internal filenames, raw stack, or user details.
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(error, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(error, indent=2, sort_keys=True))
        return 2

if __name__ == "__main__":
    sys.exit(main())
