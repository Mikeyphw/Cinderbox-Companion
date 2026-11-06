#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
SERIAL=emulator-5554
[[ "$(adb -s "$SERIAL" get-state)" == device ]] || exit 1
[[ "$(adb -s "$SERIAL" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || exit 1
[[ "$(adb -s "$SERIAL" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
[[ -z "$(adb -s "$SERIAL" shell pm path com.sdvsync 2>/dev/null | tr -d '\r')" ]] || exit 1
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
tests=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#tests[@]} == 1 ]] || exit 1
out="$RUNNER_TEMP/ux05bd-visual"
mkdir -p "$out"
printf '%s\n' '{"status":"NOT_RUN","hosted_emulator_only":true,"physical_device_qualified":false,"release_qualified":false}' > "$out/STATUS.json"
adb -s "$SERIAL" shell svc wifi disable >/dev/null
adb -s "$SERIAL" shell svc data disable >/dev/null
adb -s "$SERIAL" install -r -t "${app[0]}" >/dev/null
adb -s "$SERIAL" install -r -t "${tests[0]}" >/dev/null
local_hash="$(sha256sum "${app[0]}" | cut -d' ' -f1)"
installed_path="$(adb -s "$SERIAL" shell pm path com.sdvsync | tr -d '\r' | sed -n 's/^package:\(.*base.apk\)$/\1/p' | head -1)"
[[ "$installed_path" == /data/app/*/base.apk ]] || exit 1
installed_hash="$(adb -s "$SERIAL" shell sha256sum "$installed_path" | tr -d '\r' | cut -d' ' -f1)"
[[ "$installed_hash" == "$local_hash" ]] || exit 1
for viewport in '393 852' '360 800'; do
  read -r width height <<< "$viewport"
  adb -s "$SERIAL" shell wm size "$((width*2))x$((height*2))" >/dev/null
  adb -s "$SERIAL" shell wm density 320 >/dev/null
  adb -s "$SERIAL" shell settings put system font_scale 1.0 >/dev/null
  response="$(adb -s "$SERIAL" shell am instrument -w -r -e class \
    com.sdvsync.qualification.UX05DetailVisualDeviceTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner)"
  grep -Fq 'OK (1 test)' <<< "$response" || { echo UX05BD_INSTRUMENTATION_FAILED >&2; exit 1; }
  grep -Fq 'INSTRUMENTATION_CODE: -1' <<< "$response" || exit 1
  adb -s "$SERIAL" exec-out run-as com.sdvsync cat files/ux05bd-detail-fixture.png \
    > "$out/ux05bd-detail-${width}x${height}.png"
  adb -s "$SERIAL" exec-out run-as com.sdvsync cat files/ux05bd-anchors.json \
    > "$out/ux05bd-anchors-${width}x${height}.json"
done
printf '%s\n' '{"status":"PASS_SYNTHETIC_CAPTURE","hosted_emulator_only":true,"physical_device_qualified":false,"release_qualified":false}' > "$out/STATUS.json"
