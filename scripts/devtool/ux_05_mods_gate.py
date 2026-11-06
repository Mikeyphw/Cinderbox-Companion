#!/usr/bin/env python3
"""UX-05 native dark Mods source, routes and read-only safety contract."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def source(rel:str,root:Path=ROOT)->str:
    path=root/rel
    assert path.is_file() and not path.is_symlink(), 'UX05_MISSING_OR_LINKED:'+rel
    return path.read_text(encoding='utf-8')

def check(root:Path=ROOT)->dict:
    view=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt',root)
    main=source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    r48=source('app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',root)
    old=source('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt',root)
    vm=source('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt',root)
    theme=source('app/src/main/java/com/sdvsync/ui/theme/Theme.kt',root)
    tokens=source('app/src/main/java/com/sdvsync/ui/theme/CinderboxDarkTokens.kt',root)
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    contract=json.loads(source('design/cinderbox/02_CONTRACT/ux-contract.json',root))
    assert contract['reference']['sole_theme']=='dark'
    assert contract['navigation']['global_routes'][3]=='mods'
    assert 'CinderboxDarkTokens.colorScheme' in theme
    assert 'val Background = Color(0xFF101915)' in tokens
    assert main.count('composable("mods")')==1 and main.count('composable("mods_advanced")')==1
    assert main.count('ApprovedModsScreen(')==1 and main.count('ModManagerScreen(')==1
    assert 'onBrowseMods = { parentNavController.navigate("mods_browse") }' in main
    assert 'onOpenRemoteMod = { modId, source ->' in main
    assert 'parentNavController.navigate("mod_detail/${Uri.encode(modId)}/${Uri.encode(source)}")' in main
    assert 'onOpenAdvancedMods = { parentNavController.navigate("mods_advanced") }' in main
    assert 'onOpenInstalledMod = { uniqueId ->' in main
    assert 'parentNavController.navigate("installed_mod/${Uri.encode(uniqueId)}")' in main
    assert 'composable("mods_browse")' in main and 'route = "installed_mod/{uniqueId}"' in main
    assert 'startDestination = "home"' in main and 'startDestination = "main"' in main
    assert 'cinderbox.screen.mods' in view and 'cinderbox.mods.sections' in view
    for label in ('Your mods','Discover','Installed','Updates','Profiles',
                  'Browse mod catalog','No installed mods found',
                  'Check update metadata','No actionable updates listed',
                  'Manage profiles','Open advanced manager'):
        assert label in view,'UX05_APPROVED_COPY_MISSING:'+label
    for marker in ('ModManagerViewModel = koinViewModel()',
                   'state.installedMods', 'state.updates', 'state.profiles',
                   'state.isCheckingUpdates', 'state.updateError',
                   'onOpenInstalledMod(mod.manifest.uniqueID)',
                   'onBrowseMods','onOpenRemoteMod(mod.modId, mod.sourceId)',
                   'onOpenAdvancedMods','viewModel::checkForUpdates'):
        assert marker in view,'UX05_REAL_INVENTORY_OR_ROUTE_MISSING:'+marker
    for required in ('ModBrowseViewModel = koinViewModel()', 'browseViewModel.search(it)',
                     'browseViewModel.loadCategory(category)', 'browseViewModel::loadMore',
                     'browseViewModel::retry', 'browse.hasApiKey', 'browse.error',
                     'browse.installedSourceIds', 'categoryName == mod.categoryName',
                     'DiscoverSort.NAME', 'DiscoverSort.AUTHOR', 'gridMode = !gridMode',
                     'browse.mods', 'savedCards.values.toList()', 'readSavedCards(',
                     'savedCardsJson(', 'coil3.compose.AsyncImage', 'AsyncImage(',
                     'remoteModSourceIdentifier(sourceId, modId)',
                     'bookmarks.edit().putString("cards", savedCardsJson(next.values)).apply()',
                     'selectable(selected = isSelected, role = Role.Tab)',
                     'cinderbox.mods.filter', 'cinderbox.mods.search',
                     'cinderbox.mods.layout', 'cinderbox.mods.load-more'):
        assert required in view, 'UX05_DISCOVER_FEATURE_MISSING:'+required
    assert 'mod_detail/{modId}/{source}' in main
    assert 'ModDetailScreen(' in main
    for forbidden in ('File(', 'deleteRecursively(', 'installMod(', 'toggleMod(',
                      'applyProfile(', 'previewSelectedMods(', 'startDownload(',
                      'requestShizukuPermission(', 'Runtime.getRuntime()',
                      'setContent(', 'pm clear', '/storage/emulated/0/'):
        assert forbidden not in view,'UX05_UNSAFE_OPERATION_IN_OVERVIEW:'+forbidden
    assert 'fun ModManagerScreen(' in old and 'viewModel.toggleMod(' in old
    assert 'data class ModManagerState(' in vm and 'val profiles: List<ModProfile>' in vm
    assert 'val updates: Map<String, ModUpdateInfo>' in vm
    assert 'Triple(BottomTab.MODS, "Your mods", "mods")' in r48
    assert 'rule.onNodeWithText("Your mods").assertExists()' in r48
    for flag in ('release_enabled','publication_enabled',
                 'automatic_device_install','device_qualification_complete'):
        assert policy[flag] is False,'UX05_RELEASE_SAFETY_CHANGED:'+flag
    coordinator=source('app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',root)
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    return {'result':'UX05_APPROVED_DARK_MODS_SOURCE_PASS',
            'source_only':True,'four_panes':True,'nexus_discover_ui':True,'real_mod_inventory':True,
            'updates_advisory_only':True,'profile_mutations_in_legacy_only':True,
            'automatic_mod_install':False,'release_enabled':False,
            'pixel_parity_verified':False,'physical_device_qualified':False,
            'native_mod_detail_visual_redesign_complete':False}

if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
