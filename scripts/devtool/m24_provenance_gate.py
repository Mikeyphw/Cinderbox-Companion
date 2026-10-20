#!/usr/bin/env python3
from ci_workflow_contract import effective_ci_source
"""M24 CI/source-bound gate for a strictly read-only APK and Cinderbox probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[2]
SOURCES=[
    "scripts/devtool/m24_real_substrate.py",
    "scripts/devtool/test_m24_real_substrate.py",
    "scripts/devtool/m24_provenance_gate.py",
    ".devtool.toml",
    ".github/workflows/build.yml",
    ".github/workflows/devtool-android-build.yml",
    "docs/devtool/M24_AUTHENTICATED_DOWNLOAD.md",
]


def generate():
    contents={p:(ROOT/p).read_bytes() for p in SOURCES}
    probe=contents[SOURCES[0]].decode()
    cfg=tomllib.loads(contents[".devtool.toml"].decode())
    dag=cfg["targets"]["cinderbox"]["workflows"]["m24-provenance-check"]
    assert [x["id"] for x in dag]==["security","tests","gate"]
    assert cfg["wrapper"]["commands"]["m24-provenance-check"]["workflow"]=="m24-provenance-check"
    assert '"gh", "run", "download"' in probe and '"sha256sum"' in probe
    assert 'installed_source_verified' in probe and 'signed_depot_manifest_verified=False' in probe
    assert all(term not in probe for term in ['"install",','"uninstall",','"clear",','"reboot",'])
    for wf in (".github/workflows/build.yml", ".github/workflows/devtool-android-build.yml"):
        text=effective_ci_source(ROOT,wf)
        assert text.count("scripts/devtool/m24_provenance_gate.py")==1
        assert text.count("test_m24_real_substrate.py")==1
        assert text.index("scripts/devtool/m24_provenance_gate.py")<text.index("assembleDebugAndroidTest")
    head=subprocess.check_output(["git","-c",f"safe.directory={ROOT}","rev-parse","HEAD"],cwd=ROOT,text=True,timeout=10).strip()
    return dict(schema_version=1,producer="cinderbox-m24-provenance-source",
                source_commit=head,github_run_id=os.environ.get("GITHUB_RUN_ID"),
                source_sha256={p:hashlib.sha256(b).hexdigest() for p,b in sorted(contents.items())},
                overall="PASS_SOURCE_ONLY",installed_source_verified=False,
                real_device_probed=False,authenticated_steam_tested=False,
                signed_depot_manifest_verified=False,release_qualified=False,
                publication_allowed=False,
                open_obligations=["CI_APK_PAIR_DEVICE_BYTE_MATCH", "REAL_STEAM_ENTITLEMENT",
                                  "TRUSTED_DEPOT_MANIFEST_FILE_MATCH", "CONSENTED_LIVE_STAGE_TRANSFER",
                                  "REAL_CRASH_RECONNECTION_EXPERIMENT"])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    try: receipt=generate()
    except (AssertionError,OSError,KeyError,ValueError,subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(overall="FAILED_SOURCE_GATE",error_code=type(exc).__name__)))
        return 1
    output=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output)
    print(output)
    return 0
if __name__=="__main__":sys.exit(main())
