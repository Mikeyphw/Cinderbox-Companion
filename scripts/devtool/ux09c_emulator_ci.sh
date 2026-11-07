#!/usr/bin/env bash
# UX-09C01: hosted disposable API36 only; fonts=200%, viewports 393 and 360dp.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}" "${RUNNER_OS:?}"
[[ "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || exit 1
[[ "$(git rev-parse HEAD)" == "$GITHUB_SHA" ]] || exit 1
serial='emulator-5554'
[[ "$(adb -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')" == 1 ]] || { echo UX09C_PHYSICAL_DEVICE_REFUSED >&2; exit 1; }
[[ "$(adb -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')" == 36 ]] || exit 1
out="$RUNNER_TEMP/ux09c-large-text"
mkdir -p -- "$out"
adb -s "$serial" shell svc wifi disable >/dev/null
adb -s "$serial" shell svc data disable >/dev/null
shopt -s nullglob
app=(app/build/outputs/apk/debug/*.apk)
test_apk=(app/build/outputs/apk/androidTest/debug/*.apk)
[[ ${#app[@]} == 1 && ${#test_apk[@]} == 1 ]] || exit 1
adb -s "$serial" install -r "${app[0]}" >/dev/null
adb -s "$serial" install -r "${test_apk[0]}" >/dev/null
for viewport in '786x1704' '720x1600'; do
  adb -s "$serial" shell wm size "$viewport" >/dev/null
  adb -s "$serial" shell wm density 320 >/dev/null
  adb -s "$serial" shell settings put system font_scale 2.0 >/dev/null
  [[ "$(adb -s "$serial" shell settings get system font_scale | tr -d '\r')" == '2.0' ]] || { echo UX09C_FONT_SCALE_NOT_SET >&2; exit 1; }
  log="$out/.runner-${viewport}.log"
  # `am instrument` can exit 0 even when Android reports a JUnit failure.
  # Preserve only bounded, allowlisted diagnostics; never publish raw device logs.
  set +e
  adb -s "$serial" shell am instrument -w -r -e class \
    com.sdvsync.ui.ux.UxNativeAccessibilityTest \
    com.sdvsync.test/androidx.test.runner.AndroidJUnitRunner > "$log" 2>&1
  instrument_rc=$?
  set -e
  if [[ $instrument_rc -ne 0 ]] || \
     ! grep -F 'OK (3 tests)' "$log" >/dev/null || \
     ! grep -F 'INSTRUMENTATION_CODE: -1' "$log" >/dev/null; then
    width_px="${viewport%%x*}"
    width_dp="$((width_px / 2))"
    python3 -B - "$log" "$out/UX09C_TEST_FAILURE_RECEIPT_${width_dp}.json" "$viewport" "$instrument_rc" "$GITHUB_SHA" "$GITHUB_RUN_ID" <<'PYDIAGNOSTICS'
import json,re,sys
from pathlib import Path
log_path,out_path,viewport,rc,source_sha,run_id=sys.argv[1:]
lines=Path(log_path).read_text(errors='replace').splitlines()
class_name=test_name=''
failed=[]
for line in lines:
    if line.startswith('INSTRUMENTATION_STATUS: class='):
        class_name=line.split('=',1)[1].strip()
    elif line.startswith('INSTRUMENTATION_STATUS: test='):
        test_name=line.split('=',1)[1].strip()
    elif line.startswith('INSTRUMENTATION_STATUS_CODE:'):
        value=line.split(':',1)[1].strip()
        if value == '-2':
            # Report identifiers only, never error-stack text or device data.
            failed.append({'test':re.sub(r'[^A-Za-z0-9_.]', '',test_name)[:100],
                'class':re.sub(r'[^A-Za-z0-9_.]', '',class_name)[:140]})
markers=sorted(set(re.findall(r'\bUX09C_[A-Z0-9_]+', '\n'.join(lines))))[:20]
types=[name for name,pattern in (
    ('junit_failure',r'FAILURES!!!|Tests run: [0-9]+,\s*Failures:'),
    ('assertion',r'AssertionError|AssertionFailedError'),
    ('compose_node_missing',r'NoMatchingNodeException'),
    ('compose_node_not_enabled',r'not enabled|assertIsNotEnabled'),
    ('compose_idle_timeout',r'ComposeNotIdleException|not idle'),
    ('instrumentation_crash',r'INSTRUMENTATION_FAILED|Process crashed'),
) if re.search(pattern,'\n'.join(lines),re.I)]
receipt={'schema':'cinderbox-ux09c01-failed-test-v1',
    'result':'UX09C_INSTRUMENTATION_FAILURE_EVIDENCE',
    'viewport_px':viewport,'source_sha':source_sha,'run_id':run_id,
    'adb_exit_code':int(rc),'junit_tests_ok':any('OK (3 tests)' in x for x in lines),
    'android_runner_succeeded':any('INSTRUMENTATION_CODE: -1' in x for x in lines),
    'failed_tests':failed[:10], 'assertion_markers':markers,
    'failure_types':types or ['unclassified_failure'],
    'raw_device_log_included':False,
    'credentials_or_filesystem_paths_included':False}
Path(out_path).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('UX09C_HOSTED_DIAGNOSTIC',json.dumps(receipt,sort_keys=True),file=sys.stderr)
PYDIAGNOSTICS
    rm -f -- "$log"  # Never persist private logs in artifact.
    echo "UX09C_INSTRUMENTATION_FAILED_WITH_SANITIZED_RECEIPT:$viewport" >&2
    exit 1
  fi
  rm -f -- "$log"  # Never publish raw logs.
  width="${viewport%%x*}"
  width="$((width / 2))"
  for tab in home game saves mods more; do
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09c-$tab-$width.png" > "$out/$tab-$width.png"
    adb -s "$serial" exec-out run-as com.sdvsync cat "files/ux09c-$tab-$width.json" > "$out/$tab-$width.json"
  done
done
python3 -B scripts/devtool/ux09c_report.py \
  --evidence-dir "$out" --source-sha "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --app-sha "$(sha256sum "${app[0]}" | awk '{print $1}')" \
  --test-sha "$(sha256sum "${test_apk[0]}" | awk '{print $1}')"
echo UX09C_TEN_ACTUAL_200_PERCENT_TEXT_CAPTURES_NOT_DEVICE_ACCEPTANCE
