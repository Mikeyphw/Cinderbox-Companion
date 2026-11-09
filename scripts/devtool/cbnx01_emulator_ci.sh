#!/usr/bin/env bash
# CB-NX01: explicitly run the one policy instrumentation method on hosted API36.
# Identical device provisioning conventions to the passing NEX-R5/R48A lanes.
# No real Nexus credentials, web requests, physical device or release approval.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || { echo CBNX01_HOSTED_LINUX_REQUIRED >&2; exit 1; }
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || { echo CBNX01_SOURCE_SHA_MISMATCH >&2; exit 1; }
serial=emulator-5554
out="$RUNNER_TEMP/cbnx01-api36-policy"
mkdir -p "$out"
printf '%s\n' '{"status":"NOT_RUN","emulator_only":true,"physical_device_qualified":false,"live_nexus_qualified":false,"release_qualified":false}' > "$out/STATUS.json"
[[ "$(adb -s "$serial" get-state)" == device ]] || { echo CBNX01_DEVICE_UNAVAILABLE >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo CBNX01_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || { echo CBNX01_API36_REQUIRED >&2; exit 1; }
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null | tr -d '\r')" ]] || { echo CBNX01_FRESH_DEVICE_REQUIRED >&2; exit 1; }
python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || { echo CBNX01_DEBUG_APK_PAIR_REQUIRED >&2; exit 1; }
app_sha="$(sha256sum "${app[0]}" | cut -d' ' -f1)"
test_sha="$(sha256sum "${test_apk[0]}" | cut -d' ' -f1)"
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
installed_path="$(adb -s "$serial" shell pm path com.sdvsync | tr -d '\r' | sed -n 's/^package:\(.*base.apk\)$/\1/p' | head -1)"
[[ "$installed_path" == /data/app/*/base.apk ]] || { echo CBNX01_INSTALLED_APK_NOT_FOUND >&2; exit 1; }
installed_sha="$(adb -s "$serial" shell sha256sum "$installed_path" | tr -d '\r' | cut -d' ' -f1)"
[[ "$app_sha" == "$installed_sha" ]] || { echo CBNX01_INSTALLED_APK_HASH_MISMATCH >&2; exit 1; }
# Explicit target status: Gradle connectedDebugAndroidTest previously reported
# 0/0 tests after instrumentation crashed, despite successful APK compilation.
# Raw logs are temporary; upload only a sanitized, source-bound receipt.
raw="$out/.raw-instrumentation.log"
rawcat="$out/.raw-android-runtime.log"
trap 'rm -f -- "$raw" "$rawcat"' EXIT
adb -s "$serial" logcat -c >/dev/null 2>&1 || :
set +e
adb -s "$serial" shell am instrument -w -r -e class \
  com.sdvsync.mods.api.CbNx01IntentDeviceTest \
  com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$raw" 2>&1
instrument_exit=$?
adb -s "$serial" logcat -d -v brief -s AndroidRuntime:E TestRunner:I InstrumentationResultPrinter:I > "$rawcat" 2>&1
set -e
python3 -B scripts/devtool/cbnx01_instrumentation_receipt.py \
  --instrumentation-log "$raw" --logcat "$rawcat" \
  --instrument-exit "$instrument_exit" \
  --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --app-sha "$app_sha" --test-sha "$test_sha" --installed-sha "$installed_sha" \
  --output "$out/STATUS.json"
echo CBNX01_REAL_HOSTED_API36_NXM_POLICY_PASS_NOT_LIVE_NEXUS
