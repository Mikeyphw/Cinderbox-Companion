"""UX-05 host contract and fail-closed negative checks, no SDK or network."""
import unittest
from unittest.mock import patch
import ux_05_mods_gate as gate

VIEW='app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt'
MAIN='app/src/main/java/com/sdvsync/MainActivity.kt'

class ModsUxContract(unittest.TestCase):
    def test_main_source_and_service_safety(self):
        result=gate.check()
        self.assertTrue(result['real_mod_inventory'])
        self.assertFalse(result['automatic_mod_install'])
        self.assertFalse(result['release_enabled'])
        self.assertFalse(result['pixel_parity_verified'])

    def test_each_pane_is_present_and_review_routes_are_explicit(self):
        s=gate.source(VIEW)
        for pane in ('DISCOVER("Discover")', 'INSTALLED("Installed")',
                     'UPDATES("Updates")', 'PROFILES("Profiles")'):
            self.assertIn(pane,s)
        self.assertIn('onOpenAdvancedMods',s)
        self.assertIn('onOpenInstalledMod(mod.manifest.uniqueID)',s)
        self.assertIn('onBrowseMods',s)
        self.assertIn('onOpenRemoteMod(mod.modId, mod.sourceId)',s)

    def test_ui_cannot_toggle_install_or_apply_profiles(self):
        s=gate.source(VIEW)
        for method in ('toggleMod(', 'installMod(', 'applyProfile(', 'previewSelectedMods(',
                       'deleteRecursively(', 'startDownload(', 'File('):
            with self.subTest(method=method):self.assertNotIn(method,s)

    def test_previous_mod_manager_and_details_not_replaced(self):
        s=gate.source(MAIN)
        self.assertEqual(s.count('composable("mods")'),1)
        self.assertEqual(s.count('composable("mods_advanced")'),1)
        self.assertEqual(s.count('ModManagerScreen('),1)
        self.assertIn('composable("mods_browse")',s)
        self.assertIn('route = "installed_mod/{uniqueId}"',s)
        self.assertIn('route = "mod_detail/{modId}/{source}"',s)
        self.assertIn('onOpenRemoteMod = { modId, source ->',s)

    def test_discover_real_provider_and_user_actions(self):
        s=gate.source(VIEW)
        for code in ('ModBrowseViewModel = koinViewModel()', 'browseViewModel.search(it)',
                     'browseViewModel.loadCategory(category)', 'browseViewModel::loadMore',
                     'browseViewModel::retry', 'browse.error', 'browse.hasApiKey',
                     'browse.installedSourceIds', 'AsyncImage(', 'browse.mods',
                     'savedCards.values.toList()', 'readSavedCards(',
                     'bookmarks.edit().putString("cards", savedCardsJson(next.values)).apply()',
                     'selectable(selected = isSelected, role = Role.Tab)',
                     'cinderbox.mods.filter', 'cinderbox.mods.search'):
            with self.subTest(code=code): self.assertIn(code,s)

    def test_missing_nexus_key_is_not_steam_login(self):
        s=gate.source(VIEW)
        self.assertIn('Nexus connection required',s)
        self.assertIn('Steam is not required.',s)
        self.assertNotIn('steamAuthenticator.login',s)
        self.assertNotIn('sendSteamGuardCode',s)

    def test_negative_source_mutations_are_rejected(self):
        original=gate.source(VIEW)
        reader=gate.source
        for mutation in ('toggleMod(', 'startDownload(', 'applyProfile('):
            self.assertNotIn(mutation,original)
            def modified(rel,root=gate.ROOT):
                content=reader(rel,root)
                return content+'\n// '+mutation+'\n' if rel==VIEW else content
            with self.subTest(mutation=mutation):
                with patch.object(gate,'source',side_effect=modified):
                    with self.assertRaisesRegex(AssertionError,'UX05_UNSAFE_OPERATION_IN_OVERVIEW'):
                        gate.check()

if __name__=='__main__':unittest.main()
