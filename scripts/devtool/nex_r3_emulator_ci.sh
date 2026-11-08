#!/usr/bin/env bash
# Ephemeral GitHub API36 emulator only; never physical phone or real Nexus data.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 1
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
out="$RUNNER_TEMP/nex-r3-private-evidence"
mkdir -p "$out"
# Strict fail-closed R48A guard. No Nexus HTTP exits the device; the app's
# test-only OkHttp interceptor returns deterministic synthetic JSON responses.
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
  log="$out/.instrument-$width.log"
  if ! adb -s "$serial" shell am instrument -w -r -e class \
    'com.sdvsync.ui.ux.NexR3NativeJourneyTest' \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner >"$log" 2>&1 || \
    ! grep -Fx 'OK (3 tests)' "$log" >/dev/null || \
    ! grep -Fx 'INSTRUMENTATION_CODE: -1' "$log" >/dev/null; then
    grep -E 'Assertion|Exception|FAILURES!!!|INSTRUMENTATION_CODE|NEX_R3_' "$log" | tail -45 >&2 || :
    rm -f -- "$log"
    echo NEX_R3_HOSTED_INSTRUMENTATION_REFUSED >&2
    exit 1
  fi
  rm -f -- "$log"
  for stage in discover page-two detail file-review returned auth-401 rate-429 server-503 no-key; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/nex-r3-$stage-$width.png" \
      > "$out/$stage-$width.png"
  done
done
python3 -B scripts/devtool/nex_r3_evidence.py "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID"
echo NEX_R3_REAL_MAIN_ACTIVITY_SYNTHETIC_HTTP_API36_PASS_NOT_LIVE_NEXUS
