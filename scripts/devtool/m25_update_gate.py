#!/usr/bin/env python3
"""M25-02 R1 policy: no unknown update promotion, downloads or release enablement."""
import json, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def txt(path):return (ROOT/path).read_text(encoding='utf-8')
policy=txt('app/src/main/java/com/sdvsync/mods/ModUpdatePolicy.kt')
checker=txt('app/src/main/java/com/sdvsync/mods/api/SmapiUpdateChecker.kt')
store=txt('app/src/main/java/com/sdvsync/mods/ModDataStore.kt')
vm=txt('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
ui=txt('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
config=tomllib.loads(txt('.devtool.toml'))
for mark in ('NEWER, CURRENT, INSTALLED_AHEAD, UNCOMPARABLE, UNKNOWN',
             'fun assess(', 'fun isIgnored(', 'fun actionable(', 'fun ignored('):
    assert mark in policy, mark
# M25 R2 delegates candidate comparison to the strict response parser.
# The original R1 guarantee remains enforced: only NEWER is promoted.
parser=txt('app/src/main/java/com/sdvsync/mods/api/SmapiUpdateResponseParser.kt')
assert 'checkDetailed(mods).updates' in checker
assert 'SmapiUpdateResponseParser.parse(mods, results, System.currentTimeMillis())' in checker
assert 'ModUpdatePolicy.assess(mod.manifest.version, version)' in parser
assert 'status == UpdateAssessment.NEWER' in parser
assert 'Duplicate SMAPI observation' in parser
assert 'throw IllegalStateException("SMAPI update lookup unavailable", e)' in checker
for mark in ('ignoredUpdateVersions()', 'setIgnoredUpdateVersion(', 'context.modDataStore.edit',
             'parseIgnoredUpdates(', 'require(output.put(id, value) == null)'):
    assert mark in store, mark
for mark in ('rawUpdates:', 'ignoredUpdates:', 'showIgnoredUpdates:', 'updateError:',
             'ModUpdatePolicy.actionable(', 'dataStore.setIgnoredUpdateVersion(',
             'Update status unavailable; previous results retained'):
    assert mark in vm, mark
for mark in ('Ignore this version', 'Stop ignoring this version', 'Show ignored updates'):
    assert mark in ui, mark
node=config['targets']['cinderbox']['jobs']['m25-update-policy-source']
assert node['metadata']['read_only'] is True and node['metadata']['release_enabled'] is False
assert config['wrapper']['commands']['m25-update-check']['workflow']=='m25-update-check'
release=json.loads(txt('docs/security/M3_RELEASE_POLICY.json'))
for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert release[key] is False
assert 'NexusClientCollections' not in policy
print('M25_02_UPDATE_METADATA_SOURCE_PASS')
