#!/usr/bin/env bash
# Hosted GitHub Actions API36 only. Screenshots are actual MainActivity, not goldens.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 1
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
out="$RUNNER_TEMP/nex-r1-real-evidence"
mkdir -p -- "$out"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
shopt -s nullglob
apks=(app/build/outputs/apk/debug/*.apk)
tests=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#apks[@]} == 1 && ${#tests[@]} == 1 ]] || exit 1
adb -s "$serial" install -r "${apks[0]}" >/dev/null
adb -s "$serial" install -r "${tests[0]}" >/dev/null
for viewport in 786x1704 720x1600; do
  adb -s "$serial" shell wm size "$viewport" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  [[ "$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')" == 1.0 ]] || exit 1
  logfile="$out/.instrument-$viewport.log"
  if ! adb -s "$serial" shell am instrument -w -r -e class \
       com.sdvsync.ui.ux.NexR1NativeFiltersTest \
       com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner >"$logfile" 2>&1 || \
     ! grep -F 'OK (1 test)' "$logfile" >/dev/null || \
     ! grep -F 'INSTRUMENTATION_CODE: -1' "$logfile" >/dev/null || \
     grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED' "$logfile"; then
    echo "NEX_R1_HOSTED_REAL_FILTERS_FAIL:$viewport" >&2
    # Collect only the two explicitly allowlisted app-owned PNGs for debugging.
    # Never export logs, local saves, account data, or arbitrary app directories.
    width="${viewport%%x*}"; width="$((width/2))"
    for stage in mods filter; do
      name="nex-r1-$stage-$width.png"
      adb -s "$serial" exec-out run-as com.sdvsync cat "files/$name" \
        > "$out/$name" 2>/dev/null || rm -f -- "$out/$name"
      [[ ! -e "$out/$name" || -s "$out/$name" ]] || rm -f -- "$out/$name"
    done
    grep -E 'Assertion|Exception|FAILURES!!!|INSTRUMENTATION_CODE|NEX_R1_' "$logfile" | tail -70 >&2 || :
    grep -E 'Assertion|Exception|FAILURES!!!|INSTRUMENTATION_CODE|NEX_R1_' "$logfile" | tail -70 > "$out/FAILURE.txt" || :
    rm -f "$logfile"
    exit 1
  fi
  rm -f "$logfile"
  width="${viewport%%x*}"; width="$((width/2))"
  for stage in mods filter; do
    name="nex-r1-$stage-$width.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/$name" > "$out/$name"
    [[ -s "$out/$name" ]] || exit 1
  done
done
python3 -B scripts/devtool/nex_r1_evidence.py "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID"
echo NEX_R1_REAL_OFFLINE_NATIVE_FILTERS_SCREENS_PASS_NOT_GOLDENS
