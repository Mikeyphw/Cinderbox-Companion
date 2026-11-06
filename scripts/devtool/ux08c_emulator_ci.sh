#!/usr/bin/env bash
# Public synthetic fixtures on a disposable hosted Android API 36 emulator only.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial='emulator-5554'
out="$RUNNER_TEMP/ux08c-save-review"
mkdir -p "$out"
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX08C_PHYSICAL_DEVICE_REFUSED >&2;exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
[[ -z "$(adb -s "$serial" shell pm path com.sdvsync 2>/dev/null || :)" ]] || exit 1
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
testapk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#testapk[@]} == 1 ]] || exit 1
app_sha="$(sha256sum "${app[0]}" | awk '{print $1}')"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
adb -s "$serial" install -t "${app[0]}" >/dev/null
adb -s "$serial" install -t "${testapk[0]}" >/dev/null
for width in 393 360; do
  if [[ "$width" == 393 ]]; then px='786x1704'; else px='720x1600'; fi
  adb -s "$serial" shell wm size "$px" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 1.0 >/dev/null
  log="$(adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.qualification.UX08CSaveReviewDeviceTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner)"
  [[ "$log" == *'OK (3 tests)'* && "$log" == *'INSTRUMENTATION_CODE: -1'* ]] || {
    printf '%s\n' "$log" >&2;echo UX08C_SYNTHETIC_INSTRUMENTATION_FAILED >&2;exit 1;
  }
  for name in save backups unknown; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux08c-${name}-synthetic.png" > "$out/${name}-${width}.png"
  done
done
python3 - "$out" "$GITHUB_SHA" "$GITHUB_RUN_ID" "$app_sha" <<'PY'
import hashlib,json,struct,sys
from pathlib import Path
root=Path(sys.argv[1]);cases=[]
for name in ('save','backups','unknown'):
    for width,height in ((393,852),(360,800)):
        p=root/f'{name}-{width}.png';raw=p.read_bytes()
        assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        px,py=struct.unpack('>II',raw[16:24]);assert px==width*2 and 1000<=py<=height*2
        cases.append(dict(screen=name,viewport_dp=[width,height],capture_px=[px,py],sha256=hashlib.sha256(raw).hexdigest()))
receipt=dict(result='PASS_HOSTED_SYNTHETIC_SAVE_BACKUP_AND_ACTION_SEMANTICS',source_sha=sys.argv[2],
    run_id=sys.argv[3],app_sha256=sys.argv[4],cases=cases,
    real_save_qualified=False,real_backup_qualified=False,physical_device_qualified=False,
    native_pixel_parity_verified=False,release_enabled=False,publication_allowed=False)
(root/'UX08C_HOSTED_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print('UX08C_HOSTED_SYNTHETIC_PASS',len(cases))
PY
