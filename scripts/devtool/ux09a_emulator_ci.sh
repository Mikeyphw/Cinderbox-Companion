#!/usr/bin/env bash
# All operations are on a freshly provisioned, offline, hosted API36 emulator.
# No device install, account login, entitlement, real mod/save, or release action.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial='emulator-5554'
out="$RUNNER_TEMP/ux09a-native-parity"
mkdir -p "$out"
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09A_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null || :)" ]] || { echo UX09A_PREEXISTING_INSTALL_REFUSED >&2;exit 1; }
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
testapk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#testapk[@]} == 1 ]] || exit 1
app_sha="$(sha256sum "${app[0]}" | awk '{print $1}')"
test_sha="$(sha256sum "${testapk[0]}" | awk '{print $1}')"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${testapk[0]}" >/dev/null
for width in 393 360; do
  if [[ "$width" == 393 ]]; then resolution=786x1704; height=852; else resolution=720x1600; height=800; fi
  adb -s "$serial" shell wm size "$resolution" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  # Use only allowlisted synthetic screens/test names; never dump raw app/device data.
  if ! adb -s "$serial" shell am instrument -w -r -e class \
      com.sdvsync.ui.ux.UxReferenceParityTest \
      com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$out/result-$width.txt" 2>&1; then
    grep -E 'FAILURES!!!|Tests run:|INSTRUMENTATION_CODE|java.lang.AssertionError|INSTRUMENTATION_FAILED' "$out/result-$width.txt" | tail -25 >&2 || :
    echo UX09A_INSTRUMENTATION_REFUSED >&2; exit 1
  fi
  grep -F 'OK (9 tests)' "$out/result-$width.txt" >/dev/null || { echo UX09A_NINE_TESTS_REQUIRED >&2; exit 1; }
  grep -F 'INSTRUMENTATION_CODE: -1' "$out/result-$width.txt" >/dev/null || { echo UX09A_INSTRUMENTATION_NOT_SUCCESSFUL >&2; exit 1; }
  for screen in home game saves mods more; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09a-$screen.png" > "$out/$screen-$width.png"
  done
  # Clear the raw instrumentation log after checking status: it may carry system details.
  rm -f -- "$out/result-$width.txt"
done
python3 - "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID" "$app_sha" "$test_sha" <<'PY'
from pathlib import Path
import hashlib,json,struct,sys
root=Path(sys.argv[1]);cases=[]
for screen in ('home','game','saves','mods','more'):
 for width,height in ((393,852),(360,800)):
  p=root/f'{screen}-{width}.png'
  assert p.is_file(), 'UX09A_MISSING_CAPTURE'
  raw=p.read_bytes()
  assert raw[:8]==b'\x89PNG\r\n\x1a\n', 'UX09A_INVALID_PNG'
  w,h=struct.unpack('>II',raw[16:24]);assert w==width*2 and 900<=h<=height*2
  cases.append({'screen':screen,'viewport_dp':[width,height],
   'capture_px':[w,h],'sha256':hashlib.sha256(raw).hexdigest()})
receipt={'schema_version':1,'result':'UX09A_HOSTED_PARITY_SEMANTICS_PASS',
 'source_sha':sys.argv[2],'run_id':sys.argv[3],
 'app_sha256':sys.argv[4],'test_apk_sha256':sys.argv[5],
 'tested_methods':9,'screen_captures':cases,
 'real_steam_entitlement_qualified':False,'native_pixel_parity_verified':False,
 'talkback_qualified':False,'physical_device_qualified':False,
 'release_enabled':False,'publication_allowed':False}
(root/'UX09A_HOSTED_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print('UX09A_HOSTED_PARITY_SEMANTICS_PASS',len(cases),'screenshots')
PY
