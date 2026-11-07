#!/usr/bin/env bash
# UX-09C01: hosted disposable API36 only; fonts=200%, viewports 393 and 360dp.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial='emulator-5554'
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09C_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
out="$RUNNER_TEMP/ux09c-large-text"
mkdir -p -- "$out"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
adb -s "$serial" install -r "${app[0]}" >/dev/null
adb -s "$serial" install -r "${test_apk[0]}" >/dev/null
for viewport in '786x1704' '720x1600'; do
  adb -s "$serial" shell wm size "$viewport" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 2.0 >/dev/null
  [[ "$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')" == '2.0' ]] || { echo UX09C_FONT_SCALE_NOT_SET >&2; exit 1; }
  if ! adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.ui.ux.UxNativeAccessibilityTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$out/.runner-${viewport}.log" 2>&1; then
    grep -E 'FAILURES!!!|Tests run:|INSTRUMENTATION_CODE|AssertionError|INSTRUMENTATION_FAILED|Exception' \
      "$out/.runner-${viewport}.log" | tail -55 >&2 || :
    echo "UX09C_ACCESSIBILITY_INSTRUMENTATION_FAILED:$viewport" >&2; exit 1
  fi
  if ! grep -F 'OK (3 tests)' "$out/.runner-${viewport}.log" >/dev/null || \
     ! grep -F 'INSTRUMENTATION_CODE: -1' "$out/.runner-${viewport}.log" >/dev/null; then
    echo "UX09C_INCOMPLETE_INSTRUMENTATION:$viewport" >&2; exit 1
  fi
  rm -f -- "$out/.runner-${viewport}.log"  # Never publish raw logs.
  width="${viewport%%x*}"
  width="$((width / 2))"
  for tab in home game saves mods more; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09c-$tab-$width.png" > "$out/$tab-$width.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09c-$tab-$width.json" > "$out/$tab-$width.json"
  done
done
python3 -B scripts/devtool/ux09c_report.py \
  --evidence-dir "$out" --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --app-sha "$(sha256sum "${app[0]}" | awk '{print $1}')" \
  --test-sha "$(sha256sum "${test_apk[0]}" | awk '{print $1}')"
echo UX09C_TEN_ACTUAL_200_PERCENT_TEXT_CAPTURES_NOT_DEVICE_ACCEPTANCE
