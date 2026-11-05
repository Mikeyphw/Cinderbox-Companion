#!/usr/bin/env python3
"""M25-03 R1 source-only, no mod writes, no device, no Gradle."""
from pathlib import Path
import json, tomllib
ROOT=Path(__file__).resolve().parents[2]
def read(p):
    file=ROOT/p
    assert file.is_file() and not file.is_symlink(),p
    return file.read_text(encoding='utf-8')
policy=read('app/src/main/java/com/sdvsync/mods/ModSelectionPolicy.kt')
vm=read('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
ui=read('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
config=tomllib.loads(read('.devtool.toml'))
workflow=read('.github/workflows/m25-group-source.yml')
for name in ('ALL','BY_AUTHOR','FRAMEWORK','CONTENT_PACK','UPDATE_ATTENTION',
             'COMPATIBILITY','MAX_SELECTION = 512','fun preview(',
             'ModCompatibility.preview(', 'ModCompatibility.fingerprint(',
             'Destination folder collision','fun stillMatches('):
    assert name in policy, name
for forbidden in ('renameTo(', 'enableMod(', 'disableMod(', 'applyProfileSafely(',
                  'installFromZip(', 'deleteRecursively(', 'NexusClientCollections'):
    assert forbidden not in policy, forbidden
for name in ('selectionMode:', 'selectedModIds:', 'bulkPreview:', 'setGroupMode(',
             'selectVisibleMods(', 'clearModSelection(', 'toggleSelectedMod(',
             'previewSelectedMods(', 'dismissBulkPreview(',
             'ModSelectionPolicy.matches(', 'selectedModIds = emptySet()'):
    assert name in vm, name
for name in ('Group mods:', 'Select visible', 'Clear selection', 'Enable selected',
             'Disable selected', 'Bulk preview only', 'No folders were changed',
             'viewModel.toggleSelectedMod(', 'state.selectedModIds.size'):
    assert name in ui, name
assert 'fun applyBulk' not in vm and 'fileManager.applyProfileSafely(' in vm
assert 'M25_R1' not in workflow
assert 'ModSelectionPolicyTest' in workflow
assert 'm25-group-source' in config['targets']['cinderbox']['jobs']
assert config['targets']['cinderbox']['jobs']['m25-group-source']['metadata']['read_only'] is True
assert config['wrapper']['commands']['m25-group-check']['workflow']=='m25-group-check'
assert 'm25-group-check' in config['targets']['cinderbox']['workflows']
release=json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
for field in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
    assert release[field] is False
print('M25_03_R1_GROUPING_SELECTION_NON_MUTATING_PLAN_PASS')
