#!/usr/bin/env bash
# LAB06B only: five independent negative cases on disposable hosted API36 emulator.
set -euo pipefail
: "${CBNX_LAB06B_HEAD_SHA:?}" "${RUNNER_TEMP:?}" "${GITHUB_RUN_ID:?}"
test "$(git rev-parse HEAD)" = "$CBNX_LAB06B_HEAD_SHA"
serial=emulator-5554
out="$RUNNER_TEMP/cbnx06-lab06b"
mkdir -p "$out"
printf '%s\n' '{"schema":"cbnx06-lab06b-negative-matrix-api36-v1","status":"NOT_RUN","emulator_only":true,"physical_qualified":false,"live_iceraven_qualified":false,"release_qualified":false}' > "$out/STATUS.json"
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
test "$(adb -s "$serial" shell pm path com.sdvsync.cbnx06lab | tr -d '\r' | grep -c '/base.apk')" = 1
rawdir=$(mktemp -d "$RUNNER_TEMP/cbnx06-lab06b-raw.XXXXXXXX")
trap 'rm -rf -- "$rawdir"' EXIT
methods=(
 changedArchiveBytesCannotReachMods
 forgedNexusProvenanceCannotReachMods
 incorrectApprovalKeyCannotReachMods
 interruptedIntentRequiresManualReview
 completedRollbackCannotReplayOrReinstall
)
: > "$rawdir/exits.tsv"
for method in "${methods[@]}"; do
  # The ONLY reset is of the disposable LAB app; do NOT clear Cinderbox production.
  cleared=$(adb -s "$serial" shell pm clear com.sdvsync.cbnx06lab | tr -d '\r')
  test "$cleared" = Success || { echo LAB06B_REFUSED_LAB_RESET_FAILED; exit 2; }
  unset cleared
  set +e
  timeout 180s adb -s "$serial" shell am instrument -w -r -e class \
    "com.sdvsync.mods.CbNxLab06bNegativeDeviceTest#$method" \
    com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner \
    > "$rawdir/$method.log" 2>&1
  code=$?
  set -e
  printf '%s %s\n' "$method" "$code" >> "$rawdir/exits.tsv"
done
python3 -B scripts/devtool/cbnx06_lab06b_receipt.py \
  --raw-dir "$rawdir" --source "$CBNX_LAB06B_HEAD_SHA" --run "$GITHUB_RUN_ID" \
  --apk "$app_sha" --test-apk "$test_sha" --output "$out/STATUS.json"
echo LAB06B_API36_FIVE_NEGATIVE_CASES_PASS_PHYSICAL_DEFERRED
