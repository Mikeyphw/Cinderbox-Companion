import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def text(path): return (ROOT / path).read_text(encoding='utf-8')

class M25SourceTests(unittest.TestCase):
    def test_metadata_only_export_and_input_bounds(self):
        c = text('app/src/main/java/com/sdvsync/mods/profile/PortableProfileCodec.kt')
        for mark in ('MAX_PORTABLE_BYTES = 262144', 'MAX_MODS = 512',
                     'onMalformedInput(CodingErrorAction.REPORT)', 'Duplicate or invalid SMAPI UniqueID'):
            self.assertIn(mark, c)
        self.assertNotIn('getNexusApiKey', c)
        self.assertNotIn('downloadMod', c)
    def test_legacy_read_cannot_silently_erase_profiles(self):
        c = text('app/src/main/java/com/sdvsync/mods/ModDataStore.kt')
        self.assertIn('PortableProfileCodec.decodeStored', c)
        self.assertNotIn('private fun parseProfiles(json:', c)
        self.assertIn('context.modDataStore.edit', c)
    def test_import_save_is_separate_from_apply_and_installs(self):
        c = text('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
        block = c.split('fun savePortableImport(name: String)')[1].split('fun saveProfileNote')[0]
        self.assertNotIn('applyProfileSafely', block)
        self.assertNotIn('installFromZip', block)
        self.assertIn('dataStore.saveProfile', block)
    def test_resave_keeps_existing_profile_id_and_notes(self):
        generator = text('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt')
        self.assertIn('val prior = dataStore.getProfiles().firstOrNull', generator)
        self.assertIn('prior?.copy(enabledModIds = ids,', generator)
        self.assertIn('require(prior?.isProtected != true)', generator)
        self.assertIn('dataStore.saveProfile(profile)', generator)

    def test_compact_dialogs_remain_scrollable(self):
        screen = text('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt')
        self.assertGreaterEqual(screen.count('verticalScroll(rememberScrollState())'), 2)
        self.assertIn('Modifier.heightIn(max = 360.dp)', screen)

    def test_release_and_device_gates_off(self):
        p = json.loads(text('docs/security/M3_RELEASE_POLICY.json'))
        for f in ('release_enabled', 'publication_enabled', 'automatic_device_install',
                  'device_qualification_complete'):
            self.assertIs(p[f], False)

class M25EmulatorWiringTests(unittest.TestCase):
    def test_reuse_one_mmrllsposed_api36_avd(self):
        w = text('.github/workflows/r48-real-activity-acceptance.yml')
        self.assertEqual(w.count('ReactiveCircus/android-emulator-runner@'), 1)
        for needle in ('api-level: 36', 'target: google_apis', 'arch: x86_64',
                       'profile: pixel_6', 'cores: 2', 'ram-size: 2048M',
                       'r48_emulator_ci.sh', 'm25_emulator_ci.py', 'm25_verify.py',
                       'm25-profile-api36-emulator-evidence'):
            self.assertIn(needle, w)
        self.assertIn('scripts/devtool/m25_profile_gate.py', w)

    def test_m25_never_inflates_r48_receipt_roster(self):
        r48 = text('scripts/devtool/r48_capture.py')
        m25 = text('scripts/devtool/m25_emulator_ci.py')
        self.assertIn('realOfflineFiveTabNavigationAndPrivatePreviews', r48)
        self.assertNotIn('M25PortableProfileDeviceTest', r48)
        self.assertIn('M25PortableProfileDeviceTest', m25)
