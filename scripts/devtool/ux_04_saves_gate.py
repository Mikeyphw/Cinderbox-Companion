#!/usr/bin/env python3
"""UX-04 approved native Saves source and release-safety gate (host-only)."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def source(rel: str,root: Path=ROOT)->str:
    f=root/rel
    assert f.is_file() and not f.is_symlink(),'UX04_MISSING_OR_SYMLINK:'+rel
    return f.read_text(encoding='utf-8')

def check(root:Path=ROOT)->dict:
    src=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt',root)
    main=source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    vm=source('app/src/main/java/com/sdvsync/ui/viewmodels/DashboardViewModel.kt',root)
    legacy=source('app/src/main/java/com/sdvsync/ui/screens/DashboardScreen.kt',root)
    r48=source('app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',root)
    theme=source('app/src/main/java/com/sdvsync/ui/theme/Theme.kt',root)
    tokens=source('app/src/main/java/com/sdvsync/ui/theme/CinderboxDarkTokens.kt',root)
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    contract=json.loads(source('design/cinderbox/02_CONTRACT/ux-contract.json',root))
    assert contract['reference']['sole_theme']=='dark'
    assert contract['navigation']['global_routes'][2]=='saves'
    assert 'CinderboxDarkTokens.colorScheme' in theme and 'val Background = Color(0xFF101915)' in tokens
    assert main.count('composable("saves")')==1 and main.count('composable("saves_advanced")')==1
    assert 'ApprovedSavesScreen(' in main and 'DashboardScreen(' in main
    assert 'isSteamConnected = steamConnection == ConnectionState.LOGGED_IN' in main
    assert 'onOpenAdvancedSaves = { parentNavController.navigate("saves_advanced") }' in main
    assert 'onConnectSteam = { parentNavController.navigate("login") }' in main
    assert 'onOpenSave = { folderName -> parentNavController.navigate("save_viewer/${Uri.encode(folderName)}") }' in main
    assert 'onOpenBackups = { folderName -> parentNavController.navigate("backups/${Uri.encode(folderName)}") }' in main
    assert 'startDestination = "home"' in main and 'startDestination = "main"' in main
    assert 'cinderbox.screen.saves' in src
    for key in ('My saves','Local saves','Cloud saves','Cloud · Locked',
                'Local saves are always available','Cloud saves are optional',
                'No local saves found','No cloud saves loaded','Steam Cloud unavailable',
                'View farm','Backups','Review sync','Sync history','Import & manage saves'):
        assert key in src, 'UX04_MISSING_APPROVED_COPY:'+key
    for key in ('state.saves.filter','it.hasCloud else it.hasLocal','DashboardViewModel = koinViewModel()',
                'onOpenSave(save.folderName)','onOpenBackups(save.folderName)',
                'onOpenSyncDetail(save.folderName, save.hasCloud, save.hasLocal)',
                'onOpenAdvancedSaves','isSteamConnected && save.hasCloud',
                'if (cloudSelected && !isSteamConnected)',
                'No Steam account needed to view, back up or inspect your farms.'):
        assert key in src, 'UX04_NOT_LOCAL_FIRST:'+key
    assert 'hasLocal = folderName in localMap' in vm, 'UX04_UNPARSABLE_LOCAL_SAVE_HIDDEN'
    assert 'saveFileManager.listLocalSaves()' in vm, 'UX04_REAL_LOCAL_DISCOVERY_MISSING'
    assert 'onSaveClick:' in legacy and 'confirmImport()' in legacy, 'UX04_LEGACY_IMPORT_LOST'
    assert 'Triple(BottomTab.SAVES, "My saves", "saves")' in r48
    assert 'rule.onNodeWithText("My saves").assertExists()' in r48
    for code in ('File(', 'deleteRecursively(', 'startDownload(', 'startSync(',
                 'confirmImport(', 'backupManager.', 'syncManager.', 'createBackup(',
                 'requestShizukuPermission(', 'Runtime.getRuntime()', 'setContent(', 'pm clear'):
        assert code not in src, 'UX04_PRIVILEGED_OPERATION_IN_VIEW:'+code
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[key] is False, 'UX04_RELEASE_POLICY_CHANGED:'+key
    source('app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt',root)
    return {'result':'UX04_APPROVED_DARK_SAVES_SOURCE_PASS',
            'source_only':True,'local_first':True,'cloud_requires_steam':True,
            'real_save_inventory':True,'fake_saves':False,'automatic_sync':False,
            'legacy_import_and_sync_preserved':True,'native_pixel_parity_verified':False,
            'release_enabled':False,'physical_device_qualified':False}

if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
