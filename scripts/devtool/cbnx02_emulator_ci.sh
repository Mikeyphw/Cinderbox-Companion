#!/usr/bin/env bash
# CB-NX02B HF02: hosted API36 synthetic tests only; no Nexus credentials or real Mods.
set -euo pipefail
: "${CBNX02_HEAD_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 2
[[ "$(git rev-parse HEAD)" == "$CBNX02_HEAD_SHA" ]] || exit 2
serial=emulator-5554
out="$RUNNER_TEMP/cbnx02-api36"
mkdir -p "$out"
printf '%s\n' '{"status":"NOT_RUN","emulator_only":true,"live_nexus_qualified":false,"physical_device_qualified":false,"release_qualified":false}' > "$out/STATUS.json"
[[ "$(adb -s "$serial" get-state)" == device ]] || exit 2
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 2
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 2
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null | tr -d '\r')" ]] || exit 2
python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 2
app_sha="$(sha256sum "${app[0]}" | awk '{print $1}')"
test_sha="$(sha256sum "${test_apk[0]}" | awk '{print $1}')"
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
installed_path="$(adb -s "$serial" shell pm path com.sdvsync | tr -d '\r' | sed -n 's/^package:\(.*base.apk\)$/\1/p' | head -1)"
[[ "$installed_path" == /data/app/*/base.apk ]] || exit 2
installed_sha="$(adb -s "$serial" shell sha256sum "$installed_path" | tr -d '\r' | awk '{print $1}')"
[[ "$app_sha" == "$installed_sha" ]] || exit 2
raw="$out/.raw_instrumentation.log"
trap 'rm -f "$raw"' EXIT
set +e
adb -s "$serial" shell am instrument -w -r -e class \
  com.sdvsync.mods.CbNx02DownloadUxDeviceTest,com.sdvsync.ui.screens.CbNx02DownloadsUiDeviceTest,com.sdvsync.ui.screens.CbNx02BQueueControlsUiDeviceTest,com.sdvsync.mods.CbNx02BAdmissionDeviceTest \
  com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$raw" 2>&1
status=$?
set -e
python3 -B scripts/devtool/cbnx02_instrumentation_receipt.py \
  --log "$raw" --exit-code "$status" --source "$CBNX02_HEAD_SHA" \
  --run "$GITHUB_RUN_ID" --app-sha "$app_sha" --installed-sha "$installed_sha" \
  --test-sha "$test_sha" --output "$out/STATUS.json"
echo CBNX02B_HF02_API36_SYNTHETIC_ROSTER_PASS_NO_LIVE_PROVIDER_PROOF
