#!/usr/bin/env bash
# Disposable GitHub-hosted API36 emulator only, with synthetic settings data.
set -euo pipefail
: "${GITHUB_SHA:?}"; : "${GITHUB_RUN_ID:?}"; : "${RUNNER_TEMP:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
out="$RUNNER_TEMP/ux06-more"
mkdir -p "$out"
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX06_PHYSICAL_DEVICE_REFUSED; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null || :)" ]] || exit 1
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
app_hash="$(sha256sum "${app[0]}" | awk '{print $1}')"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${test_apk[0]}" >/dev/null
for width in 393 360; do
  if [[ "$width" == 393 ]]; then size='786x1704'; else size='720x1600'; fi
  adb -s "$serial" shell wm size "$size" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  log="$(adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.qualification.UX06MoreDeviceTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner)"
  [[ "$log" == *'OK (1 test)'* && "$log" == *'INSTRUMENTATION_CODE: -1'* ]] || {
    echo UX06_SYNTHETIC_INSTRUMENTATION_FAILED >&2
    exit 1
  }
  adb -s "$serial" exec-out run-as com.sdvsync cat files/ux06-more-synthetic.png > "$out/ux06-more-${width}.png"
done
python3 - "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID" "$app_hash" <<'PY'
from pathlib import Path
import hashlib,json,struct,sys
root=Path(sys.argv[1]);source=sys.argv[2];run=sys.argv[3];apk=sys.argv[4]
cases=[]
for width,height in ((393,852),(360,800)):
    p=root/f'ux06-more-{width}.png'
    raw=p.read_bytes()
    assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    pxw,pxh=struct.unpack('>II',raw[16:24])
    assert pxw==width*2 and 1000<=pxh<=height*2
    cases.append({'viewport_dp':[width,height], 'capture_px':[pxw,pxh],
                  'sha256':hashlib.sha256(raw).hexdigest()})
receipt={'source_sha':source,'run_id':run,'app_sha256':apk,
         'result':'PASS_SYNTHETIC_API36_MORE_SEMANTICS_AND_CAPTURE',
         'cases':cases,'real_steam_qualified':False,'real_nexus_qualified':False,
         'physical_device_qualified':False,'visual_parity_verified':False,
         'release_enabled':False,'publication_allowed':False}
(root/'UX06_MORE_EMULATOR_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print('UX06_HOSTED_MORE_SEMANTICS_AND_SCREENSHOTS_PASS',len(cases))
PY
