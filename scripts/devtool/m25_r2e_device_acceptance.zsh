#!/usr/bin/env zsh
# Opt-in physical device read-only observations; NO APK install, game stop or file writes.
setopt ERR_EXIT PIPE_FAIL NO_UNSET
serial=''
ack=0
probe_root=0
while (( $# > 0 )); do
  case "$1" in
    --serial) (( $# >= 2 )) || { print -u2 -- 'Missing --serial value'; exit 2; }; serial="$2"; shift 2 ;;
    --ack-read-only) ack=1; shift ;;
    --probe-root) probe_root=1; shift ;;
    *) print -u2 -- "Unknown option: $1"; exit 2 ;;
  esac
done
[[ "$ack" == 1 && -n "$serial" && "$serial" != emulator-* ]] || {
  print -u2 -- 'Usage: zsh m25_r2e_device_acceptance.zsh --serial localhost:5555 --ack-read-only [--probe-root]'; exit 2
}
(( $+commands[adb] )) || { print -u2 -- 'adb not on PATH'; exit 2; }
(( $+commands[python3] )) || { print -u2 -- 'python3 not on PATH'; exit 2; }
[[ "$(adb -s "$serial" get-state 2>/dev/null)" == device ]] || {
  print -u2 -- 'Target device unavailable'; exit 2
}
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" != 1 ]] || {
  print -u2 -- 'Physical device required'; exit 2
}
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || {
  print -u2 -- 'R2E acceptance scoped to Android API 36'; exit 2
}
[[ "$(adb -s "$serial" shell pm path com.sdvsync)" == *'package:'* ]] || {
  print -u2 -- 'Cinderbox debug app not installed'; exit 2
}
[[ "$(adb -s "$serial" shell pm list instrumentation)" == *'com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner'* ]] || {
  print -u2 -- 'Cinderbox Android-test APK/runner not installed. Install a matching GitHub-built pair separately with consent.'; exit 2
}
# Keep raw instrumentation output private: only accept four fixed tokens.
function run_probe() {
  local method="$1"
  local provider="$2"
  local log rc status observed
  set +e
  log="$(adb -s "$serial" shell am instrument -w -r -e class "com.sdvsync.mods.GameSessionDeviceProbeTest#$method" com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" != 0 || "$log" != *'OK (1 test)'* || "$log" != *'INSTRUMENTATION_CODE: -1'* ]]; then
    print -r -- 'FAILED'; return
  fi
  if [[ "$log" != *"R2E_PROVIDER=$provider"* || "$log" != *'R2E_LIVE_MOD_WRITES=DISABLED'* ]]; then
    print -r -- 'FAILED'; return
  fi
  if [[ "$log" == *'R2E_RESULT=OBSERVED'* ]]; then print -r -- 'OBSERVED'; return; fi
  if [[ "$log" == *'R2E_RESULT=INCONCLUSIVE'* ]]; then print -r -- 'INCONCLUSIVE'; return; fi
  print -r -- 'FAILED'
}
print -- '=== Read-only physical device diagnostics (no install, no Mods writes) ==='
local_shizuku="$(run_probe shizukuReadOnlyDiagnostic SHIZUKU)"
local_root='NOT_REQUESTED'
if (( probe_root )); then local_root="$(run_probe rootReadOnlyDiagnostic ROOT)"; fi
# Do not persist device identifiers, PIDs, game inventory or private paths.
python3 - "$local_shizuku" "$local_root" <<'PY'
import json,sys
shizuku,root=sys.argv[1:]
print(json.dumps({'schema':1,'physical_device_probe':True,'source_identity_verified':False,
  'shizuku_observation':shizuku,'root_observation':root,
  'game_idle_lock_qualified':False,'live_bulk_apply_enabled':False,
  'note':'OBSERVED means a process observation was obtained; NOT a production write approval.'},sort_keys=True))
if 'FAILED' in (shizuku,root):sys.exit(1)
PY
