#!/usr/bin/env python3
"""M25-03 R2C isolated fixture integration gate. No Gradle/device operations."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2]
def source(relative):
    p=ROOT/relative
    assert p.is_file() and not p.is_symlink(),relative
    return p.read_text(encoding='utf-8')
manager=source('app/src/main/java/com/sdvsync/mods/ModFileManager.kt')
vm=source('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
screen=source('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
tests=source('app/src/androidTest/java/com/sdvsync/mods/ModBulkControlledFixtureDeviceTest.kt')
runner=source('scripts/devtool/m25_r2c_emulator.sh')
policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json'))
for token in ('internal fun commitIsolatedBulkFixture(', 'private var isolatedBulkReview:',
              'approved === held.first', 'prepared', 'held.second',
              'context.cacheDir.canonicalFile', 'rootPath.startsWith(cachePath)',
              'bulkTransactions.apply(held.second, now.inventoryFingerprint)',
              'preparedBulk', 'private fun scanBulkInventoryNoMigrations('):
    assert token in manager,token
assert 'fun applyBulk' not in manager
assert 'fun applyBulk' not in vm
assert 'commitIsolatedBulkFixture' not in vm
assert 'commitIsolatedBulkFixture' not in screen
assert 'viewModel.applyBulk' not in screen
assert 'Bulk preview only' in screen and 'Live bulk apply is not enabled' in screen
assert 'private var isolatedBulkReview' in manager
cases=re.findall(r'@Test fun (\w+)\(',tests)
assert len(cases)==8 and len(set(cases))==8,cases
assert 'Files.createTempDirectory(context.cacheDir.toPath()' in tests
assert 'CinderboxPaths.MODS_DIR' not in tests
assert 'commitIsolatedBulkFixture(preview)' in tests
assert 'physical_device_qualified":false' in runner
assert 'live_bulk_apply_enabled":false' in runner
for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert policy[key] is False,key
print('M25_03_R2C_ISOLATED_FIXTURE_ONLY_SOURCE_PASS cases=',len(cases))
