#!/usr/bin/env python3
"""R2E source safety contract. Never runs root, Gradle, Android or game-file writes."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[2]
def read(rel):
    p=root/rel
    assert p.is_file() and not p.is_symlink(),rel
    return p.read_text()
monitor=read('app/src/main/java/com/sdvsync/autosync/GameProcessMonitor.kt')
trans=read('app/src/main/java/com/sdvsync/autosync/GameSessionTransitionPolicy.kt')
tests=read('app/src/test/java/com/sdvsync/autosync/GameSessionTransitionPolicyTest.kt')
android=read('app/src/androidTest/java/com/sdvsync/mods/GameSessionDeviceProbeTest.kt')
script=read('scripts/devtool/m25_r2e_device_acceptance.zsh')
runner=read('scripts/devtool/m25_r2e_emulator.sh')
service=read('app/src/main/java/com/sdvsync/autosync/AutoSyncService.kt')
status=read('app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
workflow=read('.github/workflows/m25-bulk-r2e.yml')
policy=json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
assert 'GameSessionProbe().observe()' in monitor
assert 'GameSessionTransitionPolicy()' in monitor
assert 'GameSessionObservation.UNKNOWN' in monitor
assert '_isGameRunning.value = observation != GameSessionObservation.NOT_OBSERVED' in monitor
assert 'val rechecked = GameSessionProbe().observe()' in monitor
assert 'if (rechecked == GameSessionObservation.NOT_OBSERVED)' in monitor
assert 'onGameStopped()' in monitor and 'onGameStarted()' in monitor
assert 'Runtime.getRuntime().exec' not in monitor and 'pidof ' not in monitor
assert 'STOP_CANDIDATE_CONFIRMED' in trans and 'GameSessionObservation.UNKNOWN' in trans
assert 'absentCount = 0' in trans and '++absentCount < 2' in trans
assert len(re.findall(r'@Test fun (\w+)\(',tests))==8
assert all(x in android for x in ('policyOnlyDoesNotAccessPrivilegedServices', 'shizukuReadOnlyDiagnostic', 'rootReadOnlyDiagnostic'))
assert 'commitIsolatedBulkFixture' not in android and 'CinderboxPaths.MODS_DIR' not in android
assert 'GameSessionSafety.permitsLiveBulkWrite' in android
assert 'R2E_LIVE_MOD_WRITES' in android and 'DISABLED' in android
assert '--ack-read-only' in script and '--probe-root' in script
assert 'adb -s "$serial" shell' in script
assert 'adb install' not in script and 'adb uninstall' not in script
assert 'pm clear' not in script and 'force-stop' not in script
assert 'GameSessionDeviceProbeTest' in runner and 'ro.kernel.qemu' in runner
assert 'isRootExplicitlyEnabled()' in service
assert 'permitsLiveBulkWrite(observation: GameSessionObservation): Boolean = false' in status
assert 'R2E_APP_TEST_APKS' in workflow
for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert policy[k] is False,k
print('M25_03_R2E_FAIL_CLOSED_TRANSITION_AND_DEVICE_SOURCE_PASS: 8 JVM + 3 Android tests')
