#!/usr/bin/env bash
# Hosted x86_64 API36 emulator only. Reuses current UX09B receipt and same APK pair.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09B2_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
out="$RUNNER_TEMP/ux09b-native-fidelity"
# The previous step installs the pair and captures 17 actual offline states.
bash scripts/devtool/ux09b_emulator_ci.sh
[[ -s "$out/UX09B_EVIDENCE.json" ]] || { echo UX09B2_BASE_RECEIPT_MISSING >&2; exit 1; }
[[ -n "$(adb -s "$serial" shell pm path com.sdvsync)" ]] || exit 1
adb -s "$serial" shell wm size '786x1704' >/dev/null
adb -s "$serial" shell wm density 320 >/dev/null
adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
# No account, network enablement, root, Shizuku, file permission or repair operation.
if ! adb -s "$serial" shell am instrument -w -r -e class \
  com.sdvsync.ui.ux.UxNativeDeepCaptureTest \
  com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$out/.ux09b2-runner.log" 2>&1; then
  grep -E 'FAILURES!!!|Tests run:|INSTRUMENTATION_CODE|AssertionError|INSTRUMENTATION_FAILED' "$out/.ux09b2-runner.log" | tail -30 >&2 || :
  echo UX09B2_DEEP_INSTRUMENTATION_FAILED >&2; exit 1
fi
if ! grep -F 'OK (4 tests)' "$out/.ux09b2-runner.log" >/dev/null || ! grep -F 'INSTRUMENTATION_CODE: -1' "$out/.ux09b2-runner.log" >/dev/null; then
  echo UX09B2_FOUR_DEEP_TESTS_REQUIRED >&2; exit 1
fi
rm -f -- "$out/.ux09b2-runner.log"  # Never publish raw device log.
for case_id in download-queue file-access operation-center installation-health; do
  adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09b2-$case_id.png" > "$out/$case_id-393.png"
  adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09b2-$case_id.json" > "$out/$case_id-393.json"
done
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
python3 -B scripts/devtool/ux09b2_report.py \
  --evidence-dir "$out" \
  --reference-dir design/cinderbox/01_REFERENCE/screenshots \
  --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --app-sha "$(sha256sum "${app[0]}" | awk '{print $1}')" \
  --test-sha "$(sha256sum "${test_apk[0]}" | awk '{print $1}')"
echo UX09B2_TWENTY_ONE_ACTUAL_COMPOSE_CASES_RECORDED
