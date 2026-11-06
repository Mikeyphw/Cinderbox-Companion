#!/usr/bin/env bash
set -euo pipefail
[[ "$(adb shell getprop ro.kernel.qemu | tr -d '\r')" = 1 ]] || { echo R2E_EMULATOR_ONLY_REFUSED >&2; exit 1; }
[[ "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = 36 ]] || { echo R2E_API36_REQUIRED >&2; exit 1; }
mapfile -t app < <(find app/build/outputs/apk/debug -maxdepth 1 -type f -name '*.apk')
mapfile -t testapk < <(find app/build/outputs/apk/androidTest/debug -maxdepth 1 -type f -name '*.apk')
[[ ${#app[@]} = 1 && ${#testapk[@]} = 1 ]] || { echo R2E_APK_PAIR_MISSING >&2; exit 1; }
adb install -r "${app[0]}" >/dev/null
adb install -r "${testapk[0]}" >/dev/null
set +e
result="$(adb shell am instrument -w -r -e class 'com.sdvsync.mods.GameSessionDeviceProbeTest#policyOnlyDoesNotAccessPrivilegedServices' com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner 2>&1)"
rc=$?
set -e
[[ "$rc" = 0 && "$result" == *'OK (1 test)'* && "$result" == *'INSTRUMENTATION_CODE: -1'* ]] || { echo R2E_EMULATOR_POLICY_FAIL >&2; exit 1; }
[[ "$result" == *'R2E_PROVIDER=POLICY'* && "$result" == *'R2E_LIVE_MOD_WRITES=DISABLED'* ]] || { echo R2E_EMULATOR_STATUS_MISSING >&2; exit 1; }
echo R2E_API36_EMULATOR_NO_PRIVILEGED_CALLS_PASS
