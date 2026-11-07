#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == '1' ]] || { echo UX09C02_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == '36' ]] || exit 1
out="$RUNNER_TEMP/ux09c02-real-chrome";mkdir -p -- "$out"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
adb -s "$serial" install -r "${app[0]}" >/dev/null
adb -s "$serial" install -r "${test_apk[0]}" >/dev/null
failure=0
for spec in '786x1704:100:1.0' '786x1704:200:2.0' '720x1600:100:1.0' '720x1600:200:2.0'; do
  IFS=: read -r viewport percent scale <<< "$spec"
  adb -s "$serial" shell wm size "$viewport" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale "$scale" >/dev/null
  actual="$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')"
  [[ "$actual" == "$scale" ]] || { echo UX09C02_FONT_SCALE_REFUSED >&2; exit 1; }
  logfile="$out/.instrumentation-${viewport}-${percent}.log"
  if ! adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.ui.ux.UxDeviceChromeTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$logfile" 2>&1; then failure=1; fi
  if ! grep -F 'OK (3 tests)' "$logfile" >/dev/null || \
     ! grep -F 'INSTRUMENTATION_CODE: -1' "$logfile" >/dev/null || \
     grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED|INSTRUMENTATION_CODE: [^ -]' "$logfile"; then
     failure=1
  fi
  if (( failure != 0 )); then
    echo "UX09C02_INSTRUMENTATION_REFUSED:${viewport}:${percent}" >&2
    grep -E 'FAILURES!!!|Test[s]? run:|Assertion|Exception|Error in|INSTRUMENTATION_CODE|UX09C02_STAGE_|UX09C02_' "$logfile" | tail -90 >&2 || :
    python3 - "$logfile" "$out/UX09C02_FAILURE.txt" <<'PYFAIL'
import re,sys,pathlib
s=pathlib.Path(sys.argv[1]).read_text(errors='replace')
lines=[x[:250] for x in s.splitlines() if re.search(r'FAILURES!!!|Tests run:|AssertionError|Error in|UX09C02_STAGE_|UX09C02_|INSTRUMENTATION_CODE:',x)]
pathlib.Path(sys.argv[2]).write_text('UX09C02_HOSTED_FAILURE\n'+'\n'.join(lines[-30:])+'\n')
PYFAIL
    rm -f -- "$logfile"
    exit 1
  fi
  rm -f -- "$logfile"
  width="${viewport%%x*}";width="$((width/2))"
  for case in home steam mods; do
    key="ux09c02-$case-$width-$percent"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/$key.png" > "$out/$key.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/$key.json" > "$out/$key.json"
  done
done
python3 -B scripts/devtool/ux09c02_report.py \
  --evidence "$out" --source "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID"
echo UX09C02_TWELVE_REAL_OFFLINE_UI_CAPTURES_NOT_PHYSICAL_DEVICE_ACCEPTANCE
