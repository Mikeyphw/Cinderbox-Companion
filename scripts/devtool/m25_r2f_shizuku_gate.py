#!/usr/bin/env python3
"""R2F source qualification: typed Shizuku reason, bounded connection retry, no live writes."""
from pathlib import Path
import json, re
ROOT=Path(__file__).resolve().parents[2]
def source(relative):
    p=ROOT/relative
    assert p.is_file() and not p.is_symlink(), relative
    return p.read_text(encoding='utf8')
shizuku=source('app/src/main/java/com/sdvsync/fileaccess/ShizukuFileAccess.kt')
reasons=source('app/src/main/java/com/sdvsync/fileaccess/ShizukuGameDiagnostic.kt')
tests=source('app/src/test/java/com/sdvsync/fileaccess/ShizukuGameDiagnosticTest.kt')
device=source('app/src/androidTest/java/com/sdvsync/mods/GameSessionDeviceProbeTest.kt')
manager=source('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
viewmodel=source('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
safety=source('app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
runner=source('scripts/devtool/m25_r2f_shizuku_device.zsh')
policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json'))
for marker in ('BINDER_NOT_READY','PERMISSION_DENIED','PERMISSION_CHECK_FAILED',
               'SERVICE_BIND_FAILED','SERVICE_TIMEOUT','SERVICE_DISCONNECTED',
               'REMOTE_CALL_FAILED','PROCESS_UNKNOWN','RUNNING(40)','NOT_OBSERVED(41)'):
    assert marker in reasons, marker
for marker in ('fun queryGameStatusDiagnostic(): ShizukuGameDiagnostic',
               'Shizuku.checkSelfPermission()', 'Shizuku.bindUserService(userServiceArgs, serviceConnection)',
               'withTimeoutOrNull(2500L)', 'withTimeoutOrNull(1500L)',
               'delay(75L)', 'ShizukuDiagnosticPolicy.fromProcessCode(',
               'fun queryGameStatus(): Int?', 'onServiceDisconnected(',
               'ShizukuGameDiagnostic.SERVICE_TIMEOUT', 'ShizukuGameDiagnostic.REMOTE_CALL_FAILED'):
    assert marker in shizuku, marker
assert 'Shizuku.requestPermission(' not in shizuku.split('suspend fun queryGameStatusDiagnostic()')[1].split('private fun requireService')[0]
assert 'R2E_SHIZUKU_DIAGNOSTIC' in device
assert 'ShizukuFileAccess.queryGameStatusDiagnostic()' in device
assert 'receipt("SHIZUKU", observed, diagnostic.name)' in device
assert 'shizukuReadOnlyDiagnostic' in device and 'rootReadOnlyDiagnostic' in device
assert len(set(re.findall(r'@Test fun (\w+)\(', tests))) == 10
assert 'live_bulk_apply_enabled' in runner and 'false' in runner
assert 'adb install' not in runner and 'adb uninstall' not in runner
assert 'fun applyBulk' not in manager and 'fun applyBulk' not in viewmodel
assert 'commitIsolatedBulkFixture' not in viewmodel
assert 'permitsLiveBulkWrite(observation: GameSessionObservation): Boolean = false' in safety
for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert policy[k] is False,k
print('R2F_SHIZUKU_TYPED_BOUNDED_FAIL_CLOSED_SOURCE_PASS')
