#!/usr/bin/env bash
# CI only: one fresh API36 x86_64 emulator, three in-memory UI-only previews.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial='emulator-5554'
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09B3_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
# 21 genuine, network-disabled MainActivity captures first; do not change their semantics.
bash scripts/devtool/ux09b2_emulator_ci.sh
out="$RUNNER_TEMP/ux09b-native-fidelity"
[[ -s "$out/UX09B2_EVIDENCE.json" && -s "$out/UX09B_EVIDENCE.json" ]] || exit 1
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
adb -s "$serial" shell wm size '786x1704' >/dev/null
adb -s "$serial" shell wm density 320 >/dev/null
adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
if ! adb -s "$serial" shell am instrument -w -r -e class \
  com.sdvsync.ui.ux.UxNativeFixtureCaptureTest \
  com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$out/.ux09b3-instrumentation.log" 2>&1; then
  grep -E 'FAILURES!!!|Tests run:|INSTRUMENTATION_CODE|AssertionError|INSTRUMENTATION_FAILED|Exception' \
    "$out/.ux09b3-instrumentation.log" | tail -45 >&2 || :
  echo UX09B3_FIXTURE_INSTRUMENTATION_FAILED >&2
  exit 1
fi
if ! grep -F 'OK (3 tests)' "$out/.ux09b3-instrumentation.log" >/dev/null || \
   ! grep -F 'INSTRUMENTATION_CODE: -1' "$out/.ux09b3-instrumentation.log" >/dev/null; then
  echo UX09B3_THREE_FIXTURE_TESTS_REQUIRED >&2; exit 1
fi
rm -f -- "$out/.ux09b3-instrumentation.log"
for case_id in game-steam-connected saves-cloud-connected mod-detail; do
  adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09b3-$case_id.png" > "$out/$case_id-393.png"
  adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09b3-$case_id.json" > "$out/$case_id-393.json"
done
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
python3 -B scripts/devtool/ux09b3_report.py \
  --evidence-dir "$out" --reference-dir design/cinderbox/01_REFERENCE/screenshots \
  --layout-json design/cinderbox/02_CONTRACT/browser-layout-golden.json \
  --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --app-sha "$(sha256sum "${app[0]}" | awk '{print $1}')" \
  --test-sha "$(sha256sum "${test_apk[0]}" | awk '{print $1}')"
python3 -B scripts/devtool/ux09b4_visual_audit.py \
  --evidence-dir "$out" --reference-dir design/cinderbox/01_REFERENCE/screenshots \
  --layout-json design/cinderbox/02_CONTRACT/browser-layout-golden.json \
  --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID"
echo UX09B4_STATUS_INSETS_AND_24_CASE_GEOMETRY_AUDITED_NOT_APPROVED
echo UX09B3_24_CANDIDATE_SCREENSHOTS_NOT_VISUAL_ACCEPTANCE
