#!/usr/bin/env bash
# Synthetic public fixture only; disposable GitHub API36 emulator, never user hardware.
set -euo pipefail
: "${GITHUB_SHA:?}"; : "${GITHUB_RUN_ID:?}"; : "${RUNNER_TEMP:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial=emulator-5554
out="$RUNNER_TEMP/ux08a-deep"
mkdir -p "$out"
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX08A_PHYSICAL_DEVICE_REFUSED;exit 1; }
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
    if [[ "$width" == 393 ]]; then size='786x1704';else size='720x1600';fi
    adb -s "$serial" shell wm size "$size" >/dev/null
    adb -s "$serial" shell wm density 320 >/dev/null
    adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
    log="$(adb -s "$serial" shell am instrument -w -r -e class \
      com.sdvsync.qualification.UX08DeepStatusDeviceTest \
      com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner)"
    [[ "$log" == *'OK (2 tests)'* && "$log" == *'INSTRUMENTATION_CODE: -1'* ]] || {
        printf '%s\n' "$log" >&2
        echo UX08A_SYNTHETIC_INSTRUMENTATION_FAILED >&2
        exit 1
    }
    adb -s "$serial" exec-out run-as com.sdvsync cat files/ux08a-queue-synthetic.png > "$out/queue-${width}.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat files/ux08a-file-access-synthetic.png > "$out/file-access-${width}.png"
done
python3 - "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID" "$app_hash" <<'PY'
from pathlib import Path
import hashlib,json,struct,sys
root=Path(sys.argv[1]);source=sys.argv[2];run=sys.argv[3];apk=sys.argv[4]
cases=[]
for name in ('queue','file-access'):
    for width,height in ((393,852),(360,800)):
        png=root/f'{name}-{width}.png'
        raw=png.read_bytes()
        assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        x,y=struct.unpack('>II',raw[16:24])
        assert x==width*2 and 1000<=y<=height*2
        cases.append({'name':name,'viewport_dp':[width,height],
                      'capture_px':[x,y],'sha256':hashlib.sha256(raw).hexdigest()})
receipt=dict(source_sha=source,run_id=run,app_sha256=apk,
    result='PASS_HOSTED_SYNTHETIC_DEEP_STATUS_AND_ACTION_SEMANTICS',
    cases=cases,real_provider_qualified=False,real_device_qualified=False,
    physical_device_qualified=False,native_pixel_parity_verified=False,
    release_enabled=False,publication_allowed=False)
(root/'UX08A_DEEP_EMULATOR_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print('UX08A_HOSTED_DEEP_SEMANTICS_AND_SCREENSHOTS_PASS',len(cases))
PY
