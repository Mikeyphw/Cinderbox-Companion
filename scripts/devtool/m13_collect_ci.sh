#!/usr/bin/env bash
# Opt-in automated CI evidence collection; no APK download or device mutation.
set -euo pipefail
[[ $# -ge 1 && $# -le 3 ]] || { echo 'Usage: m13_collect_ci.sh RUN_ID [OUTPUT_DIR] [TRUSTED_COMMIT_SHA]' >&2; exit 2; }
run="$1"
[[ "$run" =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid run ID' >&2; exit 2; }
repo="$(cd "$(dirname "$0")/../.." && pwd -P)"
output="${2:-${TMPDIR:-/tmp}/cinderbox-m13-ci-$run}"
mkdir -p "$output"
out="$(cd "$output" && pwd -P)"
command -v gh >/dev/null || { echo 'GitHub CLI not found' >&2; exit 127; }
expected="${3:-$(git -C "$repo" rev-parse HEAD)}"
gh api "repos/Mikeyphw/Cinderbox-Companion/actions/runs/$run" > "$out/run.json"
gh api "repos/Mikeyphw/Cinderbox-Companion/actions/runs/$run/jobs?per_page=100" > "$out/jobs-raw.json"
# Do not silently interpret concatenated pages as a single verified job list.
python3 - "$out/jobs-raw.json" "$out/jobs.json" <<'PY'
import json,sys
with open(sys.argv[1],encoding='utf8') as f: obj=json.load(f)
if not isinstance(obj,dict) or not isinstance(obj.get('jobs'),list) or obj.get('total_count') != len(obj['jobs']):
    raise SystemExit('Invalid GitHub jobs response')
with open(sys.argv[2],'w',encoding='utf8') as f: json.dump(obj,f)
PY
python3 "$repo/scripts/devtool/m13_qualification.py" ci \
  --root "$repo" --source-sha "$expected" \
  --run-json "$out/run.json" --jobs-json "$out/jobs.json" \
  --output "$out/M13_CI_QUALIFICATION.json"
rm -f "$out/jobs-raw.json"
printf 'M13 CI evidence: %s\n' "$out/M13_CI_QUALIFICATION.json"
