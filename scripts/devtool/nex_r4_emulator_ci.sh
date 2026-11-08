#!/usr/bin/env bash
# Source-bound GitHub API36 emulator. Only synthetic local saved metadata.
set -euo pipefail
: "${GITHUB_ACTIONS:?}" "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$GITHUB_ACTIONS" == true && "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 1
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"
out="$RUNNER_TEMP/nex-r4-synthetic-private"
mkdir -p "$out"
chmod 700 "$out"
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
for width in 393 360; do
  # Destructive reset is allowed only on the exact ephemeral GitHub emulator,
  # after identity and offline guards, never on connected user hardware.
  [[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 1
  if [[ "$(adb -s "$serial" shell pm clear com.sdvsync | tr -d '\r')" != Success ]]; then
    echo NEX_R4_EMULATOR_DATA_RESET_REFUSED >&2
    exit 1
  fi
  if [[ "$width" == 393 ]]; then screen=786x1704; else screen=720x1600; fi
  adb -s "$serial" shell wm size "$screen" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  [[ "$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')" == 1.0 ]] || exit 1
  log="$out/.instrument-$width.log"
  if ! adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.ui.ux.NexR4OfflineSavedTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner >"$log" 2>&1 || \
    ! grep -Fx 'OK (1 test)' "$log" >/dev/null || \
    ! grep -Fx 'INSTRUMENTATION_CODE: -1' "$log" >/dev/null; then
    # Only test names and R4 error codes may leave the temporary raw log.
    python3 -B - "$log" "$out/diagnostic-$width.txt" <<'PYDIAG'
from pathlib import Path
import re, sys
s=Path(sys.argv[1]).read_text(errors='replace')
allowed=[]
for line in s.splitlines():
    if line.startswith(('INSTRUMENTATION_STATUS: test=', 'INSTRUMENTATION_STATUS_CODE:', 'INSTRUMENTATION_CODE:','FAILURES!!!')):
        allowed.append(line[:180])
    for code in re.findall(r'NEX_R4_REFUSED_[A-Z0-9_]+',line):
        allowed.append(code)
Path(sys.argv[2]).write_text('NEX_R4_SANITIZED_FAILURE_DIAGNOSTIC\n'+'\n'.join(allowed[-90:])+'\n')
PYDIAG
    rm -f -- "$log"
    echo NEX_R4_HOSTED_INSTRUMENTATION_REFUSED >&2
    exit 1
  fi
  rm -f -- "$log"
  for stage in saved-card offline-sheet; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/nex-r4-$stage-$width.png" >"$out/$stage-$width.png"
  done
done
python3 -B scripts/devtool/nex_r4_evidence.py "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID"
echo NEX_R4_REAL_OFFLINE_SAVED_MAIN_ACTIVITY_PASS_SYNTHETIC_ONLY
