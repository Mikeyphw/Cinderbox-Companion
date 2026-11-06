#!/usr/bin/env python3
"""Fail closed: 4 deep real-activity captures; exact approved reference and safety gates."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=(
 'app/src/androidTest/java/com/sdvsync/ui/ux/UxNativeDeepCaptureTest.kt',
 'scripts/devtool/ux09b2_emulator_ci.sh','scripts/devtool/ux09b2_report.py',
 '.github/workflows/cinderbox-ux09b2-deep-evidence.yml',
 'design/cinderbox/02_CONTRACT/ux-contract.json',
 'docs/security/M3_RELEASE_POLICY.json',
 'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt',
 'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',
 'scripts/devtool/ux09b_emulator_ci.sh',
)
CASES=('download-queue','file-access','operation-center','installation-health')
UNSAFE=('restoreBackup(', 'deleteRecursively(', 'startDownload(',
        'requestShizukuPermission(', 'setFileAccessMode(', 'forceSync(',
        'Runtime.getRuntime(', '/storage/emulated/0/', 'run-as com.sdvsync',
        'getExternalStorageDirectory(', 'performLongClick(')

def source(root:Path,path:str)->str:
 p=root/path
 assert p.is_file() and not p.is_symlink(), 'UX09B2_MISSING_OR_SYMLINK:'+path
 return p.read_text()

def check(root:Path=ROOT)->dict:
 root=Path(root)
 for name in FILES:source(root,name)
 test=source(root,FILES[0]);script=source(root,FILES[1]);report=source(root,FILES[2]);workflow=source(root,FILES[3])
 for method in ('captureDownloadQueueReadOnly','captureFileAccessReadOnly',
                'captureOperationCenterReadOnly','captureInstallationHealthReadOnly'):
  assert test.count('@Test fun '+method+'()')==1, 'UX09B2_TEST_MISSING:'+method
 for c in CASES:assert '"'+c+'"' in test, 'UX09B2_CASE_MISSING:'+c
 for tag in ('cinderbox.screen.download-queue','cinderbox.screen.file-access',
             'cinderbox.more.file-access','cinderbox.more.operations',
             'cinderbox.more.health','cinderbox.mods.download-queue'):
  assert '"'+tag+'"' in test, 'UX09B2_REAL_NAV_MISSING:'+tag
 assert 'createAndroidComposeRule<MainActivity>()' in test and 'captureToImage()' in test
 for forbidden in UNSAFE:assert forbidden not in test, 'UX09B2_UNSAFE_INSTRUMENTATION:'+forbidden
 assert 'UX09B2_PHYSICAL_DEVICE_REFUSED' in script
 assert 'bash scripts/devtool/ux09b_emulator_ci.sh' in script
 assert 'OK (4 tests)' in script and 'wm density 320' in script
 assert "'native_pixel_parity_verified':False" in report
 assert "'all_24_states_covered':False" in report
 assert "'production_credentials_faked':False" in report
 assert 'UX09B2_UNEXPECTED_GAP' in report and 'UX09B2_BASE_SOURCE_MISMATCH' in report
 assert 'api-level: 36' in workflow and 'scripts/devtool/ux09b2_emulator_ci.sh' in workflow
 assert 'if: always()' in workflow and 'scripts/devtool/ux09b_gate.py' in workflow
 policy=json.loads(source(root,FILES[5]))
 for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
  assert policy[key] is False,'UX09B2_POLICY_DRIFT:'+key
 c=json.loads(source(root,FILES[4]));ref=root/'design/cinderbox'/c['reference']['path']
 assert c['reference']['sole_theme']=='dark'
 assert ref.is_file() and not ref.is_symlink()
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==c['reference']['sha256'], 'UX09B2_REFERENCE_DRIFT'
 assert c['screenshot_cases']['count']==24
 assert ': Boolean = false' in source(root,FILES[6])
 coord=source(root,FILES[7]);assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coord
 assert 'const val DEVICE_ACCEPTED: Boolean = false' in coord
 return {'result':'UX09B2_DEEP_READ_ONLY_SOURCE_PASS','native_cases_after_hosted_run':21,
    'remaining_unqualified_reference_states':3,'approval_granted':False,'release_enabled':False}
if __name__=='__main__':
 try:print(json.dumps(check(),sort_keys=True))
 except (AssertionError,KeyError,OSError,ValueError) as e:
  print('UX09B2_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(1)
