#!/usr/bin/env bash
# LAB05: exact-source hosted API36 emulator-only Compose UI acceptance, never a physical device.
set -euo pipefail
: "${CBNX_LAB05_HEAD_SHA:?}" "${RUNNER_TEMP:?}" "${GITHUB_RUN_ID:?}"
test "$(git rev-parse HEAD)" = "$CBNX_LAB05_HEAD_SHA"
serial=emulator-5554
out="$RUNNER_TEMP/cbnx06-lab05"
mkdir -p "$out"
printf '%s\n' '{"schema":"cbnx06-lab05-ui-api36-v1","status":"NOT_RUN","emulator_only":true,"physical_qualified":false,"live_iceraven_qualified":false,"release_qualified":false}' > "$out/STATUS.json"
test "$(adb -s "$serial" get-state)" = device
test "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" = 1
test "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" = 36
test -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null | tr -d '\r')"
shopt -s nullglob
app=(app/build/outputs/apk/cbnxLab/*.apk)
test_apk=(app/build/outputs/apk/androidTest/cbnxLab/*.apk)
test "${#app[@]}" = 1 && test "${#test_apk[@]}" = 1
# HF02: createComposeRule() launches AndroidComposeTestActivity, which must be
# registered inside the custom cbnxLab APK. A debug-only dependency is not enough.
aapt=$(find "${ANDROID_HOME:?}/build-tools" -type f -name aapt -print | sort -V | tail -n 1)
if test -z "$aapt"; then
  echo LAB05_HF02_REFUSED_ANDROID_AAPT_UNAVAILABLE >&2
  exit 2
fi
manifest_xml=$("$aapt" dump xmltree "${app[0]}" AndroidManifest.xml)
if [[ "$manifest_xml" != *'androidx.compose.ui.test.junit4.android.AndroidComposeTestActivity'* ]]; then
  echo LAB05_HF02_REFUSED_COMPOSE_HOST_ACTIVITY_ABSENT >&2
  exit 2
fi
unset manifest_xml
echo LAB05_HF02_COMPOSE_HOST_ACTIVITY_PRESENT
app_sha=$(sha256sum "${app[0]}" | cut -d' ' -f1)
test_sha=$(sha256sum "${test_apk[0]}" | cut -d' ' -f1)
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
rawdir=$(mktemp -d "$RUNNER_TEMP/cbnx06-lab05-raw.XXXXXXXX")
trap 'rm -rf -- "$rawdir"' EXIT
methods=(
 unpairedConsentRemainsDisabledAfterWindowStart
 cancelSyntheticInstallDoesNotWriteModsOrJournal
 exactFileCancelKeepsRequestPendingWithoutBrowserLaunch
 userConfirmedSyntheticInstallAndRollbackRestoresEmptyLabRoot
)
: > "$rawdir/exits.tsv"
for method in "${methods[@]}"; do
  set +e
  timeout 180s adb -s "$serial" shell am instrument -w -r -e class \
    "com.sdvsync.ui.screens.CbNxLab05UiJourneyTest#$method" \
    com.sdvsync.cbnx06lab.test/androidx.test.runner.AndroidJUnitRunner \
    > "$rawdir/$method.log" 2>&1
  code=$?
  set -e
  printf '%s %s\n' "$method" "$code" >> "$rawdir/exits.tsv"
done
python3 -B scripts/devtool/cbnx06_lab05_receipt.py \
  --raw-dir "$rawdir" --source "$CBNX_LAB05_HEAD_SHA" --run "$GITHUB_RUN_ID" \
  --apk "$app_sha" --test-apk "$test_sha" --output "$out/STATUS.json"
echo CBNX06_LAB05_API36_COMPOSE_JOURNEYS_PASS_PHYSICAL_DEFERRED
