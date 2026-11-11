#!/usr/bin/env bash
# CB-NX06 LAB03A emulator-only evidence, never the user's phone or game files.
set -euo pipefail
: "${CBNX_LAB03_HEAD_SHA:?}" "${RUNNER_TEMP:?}" "${GITHUB_RUN_ID:?}"
test "$(git rev-parse HEAD)" = "$CBNX_LAB03_HEAD_SHA"
serial=emulator-5554
out="$RUNNER_TEMP/cbnx06-lab03a"
mkdir -p "$out"
printf '%s\n' '{"schema":"cbnx06-lab03a-emulator-v1","status":"NOT_RUN","emulator_only":true,"physical_qualified":false,"live_nexus_qualified":false}' > "$out/STATUS.json"
test "$(adb -s "$serial" get-state)" = device
test "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" = 1
test "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" = 36
test -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null | tr -d '\r')"
shopt -s nullglob
app=(app/build/outputs/apk/cbnxLab/*.apk)
test_apk=(app/build/outputs/apk/androidTest/cbnxLab/*.apk)
test "${#app[@]}" = 1 && test "${#test_apk[@]}" = 1
app_sha=$(sha256sum "${app[0]}" | cut -d' ' -f1)
test_sha=$(sha256sum "${test_apk[0]}" | cut -d' ' -f1)
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
# Split the two existing tests to record WHICH test failed; no test skipped.
raw="$out/.raw-preview.log"
raw_pair="$out/.raw-pairing.log"
trap 'rm -f -- "$raw" "$raw_pair"' EXIT
set +e
timeout 90s adb -s "$serial" shell am instrument -w -r -e class \
  'com.sdvsync.mods.CbNxLab03DeviceTest#syntheticArchivePreviewDoesNotModifyLabMods' \
  com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner > "$raw" 2>&1
status=$?
timeout 90s adb -s "$serial" shell am instrument -w -r -e class \
  'com.sdvsync.mods.CbNxLab03DeviceTest#labPairingRequiresConsentAndRecordsOnlyExactInboxRequest' \
  com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner > "$raw_pair" 2>&1
pair_status=$?
set -e
python3 -B scripts/devtool/cbnx06_lab03_receipt.py --raw "$raw" --exit "$status" \
  --raw-pair "$raw_pair" --exit-pair "$pair_status" \
  --source "$CBNX_LAB03_HEAD_SHA" --run "$GITHUB_RUN_ID" \
  --apk "$app_sha" --test-apk "$test_sha" --output "$out/STATUS.json"
echo CBNX06_LAB03A_HF02_ISOLATED_INSTRUMENTATION_PASS
