#!/usr/bin/env python3
"""R2D source-only gate: game process observation cannot authorize live bulk writes."""
from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[2]
def source(rel):
    p = ROOT / rel
    assert p.is_file() and not p.is_symlink(), rel
    return p.read_text(encoding='utf-8')

engine = source('app/src/main/java/com/sdvsync/mods/ModBulkTransaction.kt')
manager = source('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
probe = source('app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
vm = source('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
ui = source('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
tests = source('app/src/test/java/com/sdvsync/mods/GameSessionSafetyTest.kt')
release = json.loads(source('docs/security/M3_RELEASE_POLICY.json'))

assert 'GameSessionObservation' in probe
assert 'NOT_OBSERVED' in probe and 'UNKNOWN' in probe and 'RUNNING' in probe
assert 'permitsLiveBulkWrite(observation: GameSessionObservation): Boolean = false' in probe
assert 'ProcessBuilder("su", "-c", ROOT_PROBE)' in probe
assert 'process.waitFor(4, TimeUnit.SECONDS)' in probe
assert 'pidof com.chucklefish.stardewvalley' in probe
assert 'ps -A -o NAME' in probe
assert 'probe_code' in probe and 'exit 41' in probe
assert 'runCatching { exitCode() }.getOrNull()' in probe
assert 'fun checkGameStatusForBulk()' in vm
assert 'GameSessionProbe().observe()' in vm
assert 'bulkPreview !== opened' in vm
assert 'Text("Check game status")' in ui
assert 'No folders were changed. Live bulk apply is not enabled.' in ui
assert 'Bulk preview only' in ui
assert 'GameSessionSafety.permitsLiveBulkWrite' not in manager
assert 'commitIsolatedBulkFixture' in manager
assert 'bulkTransactions.apply(' not in vm
assert 'bulkTransactions.apply(' not in ui
assert 'commitIsolatedBulkFixture' not in vm
assert 'commitIsolatedBulkFixture' not in ui
assert 'Runtime.getRuntime().exec' not in engine
assert not re.search(r'\bfun applyBulk\b', vm)
cases = re.findall(r'@Test fun (\w+)\(', tests)
assert len(cases) == len(set(cases)) == 8, cases
for key in ('release_enabled', 'publication_enabled', 'automatic_device_install',
            'device_qualification_complete'):
    assert release[key] is False, key
print('M25_03_R2D_FAIL_CLOSED_GAME_STATUS_PASS cases=', len(cases))
