#!/usr/bin/env python3
"""UX-09B non-mutating, fail-closed source+visual evidence lane."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=(
 'app/src/androidTest/java/com/sdvsync/ui/ux/UxNativeFidelityCaptureTest.kt',
 'scripts/devtool/ux09b_report.py','scripts/devtool/ux09b_emulator_ci.sh',
 '.github/workflows/cinderbox-ux09b-native-fidelity.yml',
 'design/cinderbox/02_CONTRACT/browser-layout-golden.json',
 'design/cinderbox/02_CONTRACT/ux-contract.json',
 'docs/security/M3_RELEASE_POLICY.json',
 'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt',
 'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',
 'scripts/devtool/r48_offline_gate.py'
)

# Only observations are allowed. Never silently bless a golden via this lane.
FORBIDDEN=(
 'deleteRecursively(', 'restoreBackup(', 'startDownload(',
 'requestShizukuPermission(', 'setFileAccessMode(',
 'forceSync(', '/storage/emulated/0/', 'Runtime.getRuntime(',
 'intent.action.DELETE', 'getExternalStorageDirectory(',
)

def source(root:Path,relative:str)->str:
    file=root/relative
    assert file.is_file() and not file.is_symlink(), 'UX09B_MISSING_OR_SYMLINK:'+relative
    return file.read_text(encoding='utf8')

def check(root:Path=ROOT)->dict:
    root=Path(root)
    for name in FILES: source(root,name)
    contract=json.loads(source(root,'design/cinderbox/02_CONTRACT/ux-contract.json'))
    ref=root/'design/cinderbox'/contract['reference']['path']
    assert ref.is_file() and not ref.is_symlink()
    assert hashlib.sha256(ref.read_bytes()).hexdigest()==contract['reference']['sha256'], 'UX09B_REFERENCE_HASH_DRIFT'
    assert contract['reference']['sole_theme']=='dark'
    assert contract['screenshot_cases']=={'size_393x852':16,'size_360x800':8,'count':24}
    tests=source(root,FILES[0]);capture=source(root,FILES[1]);runner=source(root,FILES[2]);workflow=source(root,FILES[3])
    assert tests.count('@Test fun captureOfflineReferenceMatrix()')==1
    assert 'createAndroidComposeRule<MainActivity>()' in tests
    assert 'captureToImage()' in tests and 'boundsInRoot' in tests
    for case in ('home','game-local','saves-local','saves-cloud-locked',
                 'mods-discover','mods-installed','mods-updates','mods-profiles','more'):
        assert '"'+case+'"' in tests, 'UX09B_CASE_MISSING:'+case
    assert 'capture("mods-$section")' in tests and 'for (section in listOf' in tests
    assert 'source_sha' in capture and 'native_goldens_approved' in capture
    assert "'native_pixel_parity_verified':False" in capture
    assert "'full_24_case_parity_verified':False" in capture
    assert 'UX09B_REFERENCE_LAYOUT_COUNT_CHANGED' in capture
    # UX09B must reuse the independently qualified API36 offline gate. A raw
    # svc data call fails with exit 20 on telephony-less Google APIs images.
    assert 'python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"' in runner, 'UX09B_OFFLINE_GATE_MISSING'
    assert 'svc data disable' not in runner and 'svc wifi disable' not in runner, 'UX09B_UNSAFE_RADIO_SETUP'
    offline=source(root,'scripts/devtool/r48_offline_gate.py')
    for requirement in ("'ro.kernel.qemu'", "'ro.build.version.sdk'", "'airplane-mode', 'enable'",
                        "'wifi', 'disable'", "'airplane_mode_on'", "'wifi_on'",
                        "'dumpsys', 'connectivity'", 'ACTIVE_DEFAULT_NETWORK_REFUSED'):
        assert requirement in offline, 'UX09B_OFFLINE_CONTRACT_MISSING:' + requirement
    assert 'UX09B_PHYSICAL_DEVICE_REFUSED' in runner
    assert 'com.sdvsync.ui.ux.UxNativeFidelityCaptureTest' in runner
    assert 'wm density 320' in runner and 'for width in 393 360' in runner
    assert 'api-level: 36' in workflow
    assert 'scripts/devtool/ux09b_emulator_ci.sh' in workflow
    assert 'if: always()' in workflow
    assert 'scripts/devtool/ux09a_gate.py' in workflow
    assert 'python3 -B scripts/devtool/ux09b_gate.py' in workflow
    for fragment in FORBIDDEN:
        assert fragment not in tests,'UX09B_UNSAFE_TEST:'+fragment
    policy=json.loads(source(root,'docs/security/M3_RELEASE_POLICY.json'))
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[key] is False,'UX09B_RELEASE_GATE_DRIFT:'+key
    assert ': Boolean = false' in source(root,'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
    coordinator=source(root,'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt')
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    return {'result':'UX09B_SOURCE_EVIDENCE_GATE_PASS','source_only':True,
      'reference_states':24,'native_candidate_states':17,
      'native_goldens_approved':False,'full_pixel_parity_verified':False,
      'live_writes_enabled':False,'release_enabled':False}

if __name__=='__main__':
    try:print(json.dumps(check(),sort_keys=True))
    except (AssertionError,ValueError,KeyError,OSError) as e:
        print('UX09B_SOURCE_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(1)
