#!/usr/bin/env bash
set -euo pipefail
out="${RUNNER_TEMP:?}/m25-r2b-readonly"
mkdir -p "$out"
printf '%s\n' '{"overall":"NOT_RUN","emulator_only":true,"physical_device_qualified":false,"release_qualified":false,"live_bulk_apply_enabled":false}' > "$out/RECEIPT.json"
[[ "$(adb shell getprop ro.kernel.qemu | tr -d '\r')" = 1 ]]
[[ "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = 36 ]]
mapfile -t app < <(find app/build/outputs/apk/debug -maxdepth 1 -type f -name '*.apk')
mapfile -t testapk < <(find app/build/outputs/apk/androidTest/debug -maxdepth 1 -type f -name '*.apk')
[[ ${#app[@]} = 1 && ${#testapk[@]} = 1 ]]
adb install -r "${app[0]}" >/dev/null
adb install -r "${testapk[0]}" >/dev/null
[[ "$(adb shell pm list instrumentation)" == *'com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner'* ]]
# Sanitized pass/fail receipt; no raw instrumentation output leaves this process.
set +e
result="$(adb shell am instrument -w -r -e class com.sdvsync.mods.ModBulkReadOnlyDeviceTest com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner 2>&1)"
rc=$?
set -e
if [[ "$rc" != 0 ]] || [[ "$result" != *'OK (4 tests)'* ]] || [[ "$result" != *'INSTRUMENTATION_CODE: -1'* ]] || [[ "$result" == *'INSTRUMENTATION_FAILED'* ]]; then
  echo 'R2B_API36_READONLY_FIXTURES_FAILED' >&2
  exit 1
fi
printf '{"overall":"PASS","source_sha":"%s","run_id":"%s","tests_passed":4,"emulator_only":true,"physical_device_qualified":false,"release_qualified":false,"live_bulk_apply_enabled":false}\n' "$GITHUB_SHA" "$GITHUB_RUN_ID" > "$out/RECEIPT.json"
echo 'R2B_API36_READONLY_FOUR_FIXTURES_PASS'
