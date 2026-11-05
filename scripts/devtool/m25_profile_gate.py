#!/usr/bin/env python3
"""No Android/Gradle: fail-closed source checks for M25-00/M25-01."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def source(path):
    return (ROOT / path).read_text(encoding='utf-8')

codec = source('app/src/main/java/com/sdvsync/mods/profile/PortableProfileCodec.kt')
model = source('app/src/main/java/com/sdvsync/mods/models/ModProfile.kt')
store = source('app/src/main/java/com/sdvsync/mods/ModDataStore.kt')
vm = source('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
ui = source('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
config = source('.devtool.toml')
policy = json.loads(source('docs/security/M3_RELEASE_POLICY.json'))
for needle in ('MAX_PORTABLE_BYTES = 262144', 'CodingErrorAction.REPORT',
               'Duplicate or invalid SMAPI UniqueID', 'Unknown stored profile schema',
               'checkKeys(root, setOf("format", "schema_version", "profile"))'):
    assert needle in codec, needle
for needle in ('val id:', 'val notes:', 'val isProtected:', 'val modifiedAt:'):
    assert needle in model, needle
for needle in ('PortableProfileCodec.decodeStored', 'PortableProfileCodec.encodeStored',
               'context.modDataStore.edit'):
    assert needle in store, needle
for needle in ('previewPortableImport', 'savePortableImport', 'saveProfileNote',
               'exportPortableProfile', 'ModCompatibility.fingerprint'):
    assert needle in vm, needle
for needle in ('CreateDocument("application/json")', 'Import profile JSON',
               'Save profile only', 'Profile mod note'):
    assert needle in ui, needle
assert 'prior?.copy(enabledModIds = ids,' in vm
assert 'require(prior?.isProtected != true)' in vm
assert ui.count('verticalScroll(rememberScrollState())') >= 2
assert 'm25-profile-check' in config
assert 'applyProfileSafely(' not in codec
assert 'installFromZip(' not in codec
assert 'NexusClientCollections' not in codec
for flag in ('release_enabled', 'publication_enabled', 'automatic_device_install',
             'device_qualification_complete'):
    assert policy[flag] is False, flag
print('M25_PROFILE_METADATA_AND_POLICY_SOURCE_PASS')

# M25 shares the exact API36 x86_64 Linux/KVM host action already accepted
# in Cinderbox R48 and used by MMRL-LSPosed S09; no second AVD/job is created.
workflow = source('.github/workflows/r48-real-activity-acceptance.yml')
for marker in (
    'runs-on: ubuntu-24.04',
    'ReactiveCircus/android-emulator-runner@a421e43855164a8197daf9d8d40fe71c6996bb0d',
    'api-level: 36', 'target: google_apis', 'arch: x86_64', 'profile: pixel_6',
    'cores: 2', 'ram-size: 2048M', 'disk-size: 3072M',
    'r48_emulator_ci.sh', 'm25_emulator_ci.py', 'm25_verify.py',
    'scripts/devtool/r48_verify.py',
    'M25_PROFILE_EMULATOR_EVIDENCE.json',
    'if: always()',
):
    assert marker in workflow, 'M25 emulator missing invariant: ' + marker
assert workflow.count('ReactiveCircus/android-emulator-runner@') == 1
assert 'm25_emulator_ci.py' in workflow.split('script:', 1)[1]
assert workflow.index('r48_emulator_ci.sh') < workflow.index('m25_emulator_ci.py')
assert workflow.index('scripts/devtool/r48_verify.py') < workflow.index('scripts/devtool/m25_verify.py')
assert 'secrets.' not in workflow
assert 'sudo adb' not in workflow
assert 'pm clear' not in workflow
emulator_script = source('scripts/devtool/m25_emulator_ci.py')
for marker in ('ro.kernel.qemu', 'ro.build.version.sdk', 'emulator-5554',
               'installed_base_apk_sha256', 'test_count', 'raw_logs_retained',
               'test_class', 'terminal_success', 'passed_tests', 'exact_event_sequence'):
    assert marker in emulator_script
assert 'adb root' not in emulator_script
assert 'secrets.' not in emulator_script
print('M25_MMRL_PARITY_API36_INSTRUMENTATION_SOURCE_PASS')
