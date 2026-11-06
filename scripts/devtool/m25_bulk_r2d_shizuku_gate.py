#!/usr/bin/env python3
"""Shizuku-read-only game-session diagnostic; no new live Mods write callers."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2]
def text(relative):
 p=ROOT/relative
 assert p.is_file() and not p.is_symlink(),relative
 return p.read_text(encoding='utf-8')
aidl=text('app/src/main/aidl/com/sdvsync/fileaccess/IFileService.aidl')
service=text('app/src/main/java/com/sdvsync/fileaccess/FileService.kt')
shizuku=text('app/src/main/java/com/sdvsync/fileaccess/ShizukuFileAccess.kt')
probe=text('app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
vm=text('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
screen=text('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
tests=text('app/src/test/java/com/sdvsync/mods/GameSessionPrivilegedProviderTest.kt')
manager=text('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
engine=text('app/src/main/java/com/sdvsync/mods/ModBulkTransaction.kt')
assert 'int queryGameProcessStatus() = 9;' in aidl
assert 'override fun queryGameProcessStatus(): Int {' in service
assert '[ "${\'$\'}uid" = 2000 ]' in service
assert 'pidof com.chucklefish.stardewvalley' in service
assert 'ps -A -o NAME' in service
assert 'process.waitFor(4, TimeUnit.SECONDS)' in service
assert 'process.exitValue().takeIf { it == 40 || it == 41 } ?: 0' in service
assert 'queryGameProcessStatus()' in shizuku and 'withTimeoutOrNull(2500L)' in shizuku
assert '.version(2)' in shizuku
assert 'Shizuku.pingBinder()' in shizuku and 'Shizuku.checkSelfPermission()' in shizuku
assert 'fun fromProviders(shizukuCode: Int?, rootFallback:' in probe
assert 'fromRootProbeExit(shizukuCode)' in probe
assert 'permitsLiveBulkWrite(observation: GameSessionObservation): Boolean = false' in probe
assert 'ShizukuFileAccess.queryGameStatus()' in vm
assert 'GameSessionProbe().observe()' in vm
assert 'Check game status' in screen and 'Live bulk apply is not enabled' in screen
assert 'Shizuku' in screen and 'root if unavailable' in screen
assert 'fun applyBulk' not in vm and 'bulkTransactions.apply(' not in vm
assert 'commitIsolatedBulkFixture' not in vm
assert 'bulkTransactions.apply(' not in screen
assert 'fun applyBulk' not in manager
assert 'commitIsolatedBulkFixture' in manager
assert 'java.lang.Runtime.getRuntime()' not in engine
cases=re.findall(r'@Test fun (\w+)\(',tests)
assert len(cases)==len(set(cases))==5,cases
release=json.loads(text('docs/security/M3_RELEASE_POLICY.json'))
for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
 assert release[key] is False,key
print('M25_03_R2D_SHIZUKU_FIRST_ROOT_FALLBACK_PASS',len(cases))
