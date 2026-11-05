#!/usr/bin/env python3
"""Host-only M25 R2 source invariants; no Gradle, emulator, network or mod writes."""
from pathlib import Path
import json, re, tomllib
ROOT=Path(__file__).resolve().parents[2]
def source(path):
    p=ROOT/path
    assert p.is_file() and not p.is_symlink(), 'M25_R2_FILE_MISSING:'+path
    return p.read_text(encoding='utf-8')

insight=source('app/src/main/java/com/sdvsync/mods/ModUpdateInsight.kt')
codec=source('app/src/main/java/com/sdvsync/mods/ModUpdateObservationCodec.kt')
parser=source('app/src/main/java/com/sdvsync/mods/api/SmapiUpdateResponseParser.kt')
network=source('app/src/main/java/com/sdvsync/mods/api/SmapiUpdateChecker.kt')
data=source('app/src/main/java/com/sdvsync/mods/ModDataStore.kt')
vm=source('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
ui=source('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
detail=source('app/src/main/java/com/sdvsync/ui/screens/InstalledModDetailScreen.kt')
detail_vm=source('app/src/main/java/com/sdvsync/ui/viewmodels/InstalledModDetailViewModel.kt')
summary=source('app/src/main/java/com/sdvsync/ui/components/M25UpdateStatusSummary.kt')
workflow=source('.github/workflows/r48-real-activity-acceptance.yml')
unit_wf=source('.github/workflows/m25-update-source.yml')
config=tomllib.loads(source('.devtool.toml'))
policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json'))

for field in ('NEWER','CURRENT','INSTALLED_AHEAD','UNCOMPARABLE','UNKNOWN'):
    assert field in insight and field in summary
assert 'fun freshness(' in insight and 'checkedAtMs > nowMs' in insight
assert 'fun plainChangelog(' in insight and 'MAX_CHANGELOG_DISPLAY = 4000' in insight
assert 'safeUpdateUrl(' in insight and 'rawUserInfo != null' in insight
assert 'ModUpdatePolicy.assess(observation.installedVersion, candidate)' in codec
assert 'Duplicate update observation' in codec
assert 'Duplicate SMAPI observation' in parser
assert 'UpdateAssessment.UNKNOWN' in parser
assert 'SmapiUpdateResponseParser.parse(mods, results, System.currentTimeMillis())' in network
assert 'fun checkDetailed(' in network
for required in ('getUpdateObservations()', 'setUpdateSnapshot(',
                 'prefs[UPDATE_OBSERVATION_KEY] = encoded', 'prefs[LAST_UPDATE_CHECK_KEY] = snapshot.checkedAtMs'):
    assert required in data, required
assert 'dataStore.setUpdateSnapshot(result)' in vm
assert 'ModUpdateInsight.observationFor' in detail_vm
assert 'M25UpdateStatusSummary(' in ui
assert 'HtmlText(' not in detail and 'toHtmlIfFormatted(' not in detail
assert 'ModUpdateInsight.plainChangelog(updateInfo.changelogHtml)' in detail
assert 'ModUpdateInsight.safeUpdateUrl(updateInfo.updateUrl)' in detail
assert 'files.filter { it.isPrimary }.maxByOrNull' not in detail_vm
for unsafe in ('installFromZip(', 'applyProfileSafely(', 'deleteRecursively(', 'NexusClientCollections', 'getNexusApiKey'):
    for core in (insight,codec,parser,summary): assert unsafe not in core
assert 'M25R2UpdateInsightDeviceTest' in source('app/src/androidTest/java/com/sdvsync/mods/update/M25R2UpdateInsightDeviceTest.kt')
assert workflow.count('ReactiveCircus/android-emulator-runner@') == 1
assert 'api-level: 36' in workflow and 'arch: x86_64' in workflow
assert 'script: bash -c ' in workflow and 'm25_r2_emulator_ci.py' in workflow
assert workflow.index('r48_emulator_ci.sh') < workflow.index('m25_emulator_ci.py') < workflow.index('m25_r2_emulator_ci.py')
assert workflow.index('r48_verify.py') < workflow.index('m25_verify.py') < workflow.index('m25_r2_verify.py')
assert 'm25-r2-update-intelligence-api36' in workflow
assert ':app:assembleDebug :app:assembleDebugAndroidTest' in workflow
assert 'ModUpdateInsightTest' in unit_wf and 'test_m25_r2_gate.py' in unit_wf
assert config['wrapper']['commands']['m25-update-r2-check']['workflow']=='m25-update-r2-check'
assert config['targets']['cinderbox']['jobs']['m25-update-r2-source']['metadata']['read_only'] is True
for flag in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert policy[flag] is False
print('M25_R2_UPDATE_STATUS_FRESHNESS_INERT_CHANGELOG_API36_SOURCE_PASS')
