#!/usr/bin/env bash
# CB-NX03A read-only localhost tests, private synthetic fixtures, no real Nexus credentials.
set -euo pipefail
: "${CBNX03_HEAD_SHA:?}" "${RUNNER_TEMP:?}" "${GITHUB_RUN_ID:?}"
[[ "$(git rev-parse HEAD)" == "$CBNX03_HEAD_SHA" ]] || exit 2
serial=emulator-5554
out="$RUNNER_TEMP/cbnx03-api36"
mkdir -p "$out"
printf '%s\n' '{"status":"NOT_RUN","emulator_only":true,"device_qualified":false,"live_firefox_qualified":false}' > "$out/STATUS.json"
[[ "$(adb -s "$serial" get-state)" == device ]] || exit 2
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 2
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 2
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null | tr -d '\r')" ]] || exit 2
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 2
app_sha="$(sha256sum "${app[0]}" | cut -d' ' -f1)"
test_sha="$(sha256sum "${test_apk[0]}" | cut -d' ' -f1)"
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
raw="$out/.instrumentation.log"
trap 'rm -f "$raw"' EXIT
set +e
adb -s "$serial" shell am instrument -w -r -e class \
  com.sdvsync.mods.CbNx03PairingDeviceTest \
  com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$raw" 2>&1
status=$?
set -e
# The parser prints safe fixed failure categories, never raw instrumentation.
# Preserve the redacted receipt even when a test fails; raw logs are deleted.
python3 -B scripts/devtool/cbnx03_instrumentation_receipt.py \
  --log "$raw" --exit "$status" --source "$CBNX03_HEAD_SHA" \
  --run "$GITHUB_RUN_ID" --app-sha "$app_sha" --test-sha "$test_sha" \
  --output "$out/STATUS.json"
echo CBNX03_API36_SYNTHETIC_BRIDGE_PASS_NO_LIVE_FIREFOX_PROOF
