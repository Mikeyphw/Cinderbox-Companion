#!/usr/bin/env bash
# Hosted-only real offline MainActivity screenshots. Refuse any user device.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09D02_NON_EMULATOR_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || { echo UX09D02_SDK_REFUSED >&2; exit 1; }
out="$RUNNER_TEMP/ux09d02-real-route-evidence"
mkdir -p -- "$out"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
shopt -s nullglob
apks=(app/build/outputs/apk/debug/*.apk)
tests=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#apks[@]} == 1 && ${#tests[@]} == 1 ]] || { echo UX09D02_APK_COUNT_REFUSED >&2; exit 1; }
adb -s "$serial" install -r "${apks[0]}" >/dev/null
adb -s "$serial" install -r "${tests[0]}" >/dev/null
for viewport in 786x1704 720x1600; do
  adb -s "$serial" shell wm size "$viewport" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  [[ "$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')" == 1.0 ]] || exit 1
  logfile="$out/.instrumentation-$viewport.log"
  if ! adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.ui.ux.Ux09D02RealRouteEvidenceTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$logfile" 2>&1 || \
    ! grep -F 'OK (4 tests)' "$logfile" >/dev/null || \
    ! grep -F 'INSTRUMENTATION_CODE: -1' "$logfile" >/dev/null || \
    grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED' "$logfile"; then
    echo "UX09D02_REAL_ROUTES_FAILED:$viewport" >&2
    grep -E 'Assertion|Exception|Error in|FAILURES!!!|Tests run|INSTRUMENTATION_CODE|UX09D02_' "$logfile" | tail -70 >&2 || :
    python3 - "$logfile" "$out/UX09D02_FAILURE.txt" <<'PYFAIL'
import pathlib,re,sys
lines=pathlib.Path(sys.argv[1]).read_text(errors='replace').splitlines()
keep=[s[:200] for s in lines if re.search(r'Assertion|Exception|FAILURES!!!|Tests run|UX09D02_|INSTRUMENTATION_CODE',s)]
pathlib.Path(sys.argv[2]).write_text('UX09D02_HOSTED_FAILURE\n'+'\n'.join(keep[-35:])+'\n')
PYFAIL
    rm -f -- "$logfile"
    exit 1
  fi
  rm -f -- "$logfile"
  width="${viewport%%x*}"; width="$((width/2))"
  for case in home game advanced-mods steam-login operation-center; do
    stem="ux09d02-$case-$width"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/$stem.png" > "$out/$stem.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/$stem.json" > "$out/$stem.json"
  done
done
python3 -B scripts/devtool/ux09d02_report.py --evidence "$out" --source "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID"
echo UX09D02_TEN_REAL_ROUTE_SCREENSHOTS_AND_BACK_PROOF_NOT_GOLDENS
