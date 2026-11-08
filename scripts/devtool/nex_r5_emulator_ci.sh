#!/usr/bin/env bash
# Hosted x86_64 API36 only. No real user data, Nexus credentials or download requests.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 1
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
out="$RUNNER_TEMP/nex-r5-synthetic-private"
mkdir -p "$out"
python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
for width in 393 360; do
  if [[ "$width" == 393 ]]; then screen=786x1704; else screen=720x1600; fi
  adb -s "$serial" shell wm size "$screen" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  [[ "$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')" == 1.0 ]] || exit 1
  adb -s "$serial" shell pm clear com.sdvsync >/dev/null
  logfile="$out/.instrument-$width.log"
  if ! adb -s "$serial" shell am instrument -w -r -e class \
      com.sdvsync.ui.ux.NexR5UnifiedDetailTest \
      com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$logfile" 2>&1 || \
      ! grep -Fx 'OK (3 tests)' "$logfile" >/dev/null || \
      ! grep -Fx 'INSTRUMENTATION_CODE: -1' "$logfile" >/dev/null; then
    grep -E 'Assertion|Exception|FAILURES!!!|INSTRUMENTATION_CODE' "$logfile" | tail -35 >&2 || :
    echo NEX_R5_HOSTED_INSTRUMENTATION_REFUSED >&2
    rm -f -- "$logfile"
    exit 1
  fi
  rm -f -- "$logfile"
  for stage in overview files community; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/nex-r5-$stage-$width.png" > "$out/nex-r5-$stage-$width.png"
  done
done
python3 -B scripts/devtool/nex_r5_evidence.py "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID"
echo NEX_R5_REAL_HOSTED_API36_SYNTHETIC_NATIVE_PASS_NO_LIVE_NEXUS
