#!/usr/bin/env zsh
# Opt-in read-only physical device diagnosis; never installs, uninstalls or accesses Mods.
setopt ERR_EXIT PIPE_FAIL NO_UNSET
serial=''
ack=0
while (( $# > 0 )); do
  case "$1" in
    --serial) (( $# >= 2 )) || { print -u2 -- 'Missing --serial'; exit 2; }; serial="$2"; shift 2 ;;
    --ack-read-only) ack=1; shift ;;
    *) print -u2 -- "Unknown argument: $1"; exit 2 ;;
  esac
done
[[ "$ack" == 1 && -n "$serial" && "$serial" != emulator-* ]] || {
  print -u2 -- 'Usage: zsh m25_r2f_shizuku_device.zsh --serial localhost:5555 --ack-read-only'; exit 2
}
command -v adb >/dev/null || { print -u2 -- 'Missing adb'; exit 2; }
[[ "$(adb -s "$serial" get-state 2>/dev/null)" == device ]] || { print -u2 -- 'Device unavailable'; exit 2; }
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" != 1 ]] || {
  print -u2 -- 'Refusing emulator target'; exit 2
}
# Instrumentation reads Shizuku state and fixed game process only. Capture private raw logs
# in memory, print allow-listed statuses only. Never request grants or invoke root here.
log_output=''
if ! log_output="$(adb -s "$serial" shell am instrument -w -r \
  -e class 'com.sdvsync.mods.GameSessionDeviceProbeTest#shizukuReadOnlyDiagnostic' \
  com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner 2>&1)"; then
  print -u2 -- 'R2F_INSTRUMENTATION_FAILED'; exit 1
fi
[[ "$log_output" == *'OK (1 test)'* && "$log_output" == *'INSTRUMENTATION_CODE: -1'* &&
   "$log_output" == *'R2E_LIVE_MOD_WRITES=DISABLED'* &&
   "$log_output" == *'R2E_PROVIDER=SHIZUKU'* ]] || {
  print -u2 -- 'R2F_INSTRUMENTATION_CONTRACT_FAILED'; exit 1
}
reason_value="$(print -r -- "$log_output" | sed -n 's/.*R2E_SHIZUKU_DIAGNOSTIC=\([A-Z_]*\)$/\1/p')"
case "$reason_value" in
  RUNNING|NOT_OBSERVED|BINDER_NOT_READY|PERMISSION_DENIED|PERMISSION_CHECK_FAILED|SERVICE_BIND_FAILED|SERVICE_TIMEOUT|SERVICE_DISCONNECTED|REMOTE_CALL_FAILED|PROCESS_UNKNOWN) ;;
  *) print -u2 -- 'R2F_REASON_MISSING_OR_INVALID (possible stale test APK)'; exit 1 ;;
esac
print -- "R2F_SHIZUKU_DIAGNOSTIC=$reason_value"
print -- 'R2F_LIVE_BULK_WRITES=DISABLED; live_bulk_apply_enabled=false'
print -- 'R2F_SOURCE_IDENTITY=NOT_ATTESTED_BY_THIS_SCRIPT'
