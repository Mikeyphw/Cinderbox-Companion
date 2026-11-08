#!/usr/bin/env bash
# Isolated HOSTED Android API36 emulator only. Never runs against a real phone.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial='emulator-5554'
out="$RUNNER_TEMP/ux09b-native-fidelity"
mkdir -p "$out"
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09B_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || { echo UX09B_WRONG_API >&2; exit 1; }
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null || :)" ]] || { echo UX09B_PREEXISTING_APP_REFUSED >&2; exit 1; }
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || { echo UX09B_APK_PAIR_MISSING >&2; exit 1; }
app_sha="$(sha256sum "${app[0]}" | awk '{print $1}')"
test_sha="$(sha256sum "${test_apk[0]}" | awk '{print $1}')"
# Reuse the qualified R48A API36 offline gate. It verifies airplane mode,
# Wi-Fi shutdown, and no active default network without requiring a phone
# binder service (which this hosted Google APIs emulator does not provide).
# Its serial and API36 checks are fail-closed; never bypass on failure.
python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
for width in 393 360; do
  if [[ "$width" == 393 ]]; then resolution='786x1704'; else resolution='720x1600'; fi
  adb -s "$serial" shell wm size "$resolution" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  if ! adb -s "$serial" shell am instrument -w -r -e class \
      com.sdvsync.ui.ux.UxNativeFidelityCaptureTest \
      com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$out/.result-$width.txt" 2>&1; then
    grep -E 'FAILURES!!!|Tests run:|INSTRUMENTATION_CODE|java.lang.AssertionError|INSTRUMENTATION_FAILED' "$out/.result-$width.txt" | tail -25 >&2 || :
    echo UX09B_INSTRUMENTATION_FAILED >&2; exit 1
  fi
  grep -F 'OK (1 test)' "$out/.result-$width.txt" >/dev/null || { echo UX09B_TEST_NOT_GREEN >&2; exit 1; }
  grep -F 'INSTRUMENTATION_CODE: -1' "$out/.result-$width.txt" >/dev/null || { echo UX09B_RUNNER_NOT_GREEN >&2; exit 1; }
  for case_id in home game-local saves-local mods-discover mods-installed mods-updates mods-profiles more; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09b-$case_id.png" > "$out/$case_id-$width.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09b-$case_id.json" > "$out/$case_id-$width.json"
  done
  if [[ "$width" == 393 ]]; then
    adb -s "$serial" exec-out run-as com.sdvsync cat 'files/ux09b-saves-cloud-locked.png' > "$out/saves-cloud-locked-393.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat 'files/ux09b-saves-cloud-locked.json' > "$out/saves-cloud-locked-393.json"
  fi
  rm -f -- "$out/.result-$width.txt" # Don't publish raw emulator instrumentation logs.
done
python3 -B scripts/devtool/ux09b_report.py \
  --native-dir "$out" \
  --reference-dir design/cinderbox/01_REFERENCE/screenshots \
  --layout-json design/cinderbox/02_CONTRACT/browser-layout-golden.json \
  --out-dir "$out" --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --app-sha "$app_sha" --test-sha "$test_sha"
echo UX09B_NATIVE_CANDIDATES_COLLECTED
