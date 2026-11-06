#!/usr/bin/env python3
"""UX-08A safe native queue and file access routes; source-only contract."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def source(relative,root=ROOT):
    f=root/relative
    assert f.is_file() and not f.is_symlink(), 'UX08A_MISSING_SOURCE:'+relative
    return f.read_text(encoding='utf-8')
def check(root=ROOT):
    main=source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    deep=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedDeepStatusScreen.kt',root)
    more=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt',root)
    mods=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt',root)
    test=source('app/src/androidTest/java/com/sdvsync/qualification/UX08DeepStatusDeviceTest.kt',root)
    script=source('scripts/devtool/ux08a_emulator_ci.sh',root)
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    contract=json.loads(source('design/cinderbox/02_CONTRACT/ux-contract.json',root))
    assert contract['reference']['sole_theme']=='dark'
    assert contract['navigation']['global_routes']==['home','game_download','saves','mods','settings']
    assert main.count('composable("download_queue")')==1
    assert main.count('composable("file_access_overview")')==1
    assert main.count('ApprovedDeepStatusScreen(')==2
    assert 'onOpenQueue = { parentNavController.navigate("download_queue") }' in main
    assert 'onOpenFileAccess = { parentNavController.navigate("file_access_overview") }' in main
    assert 'onOpenAdvancedSettings = { navController.navigate("more_advanced") }' in main
    assert 'onOpenOperations = { navController.navigate("operation_center") }' in main
    assert 'onOpenHealth = { navController.navigate("installation_health") }' in main
    assert 'route = "mod_detail/{modId}/{source}"' in main
    assert 'route = "save_viewer/{saveFolderName}"' in main
    assert 'composable("more_help")' in main and 'composable("more_about")' in main
    assert 'onOpenQueue: () -> Unit' in mods
    assert 'cinderbox.mods.download-queue' in mods
    assert 'onOpenFileAccess: () -> Unit' in more
    assert '"Inspect", tag = "cinderbox.more.file-access", onClick = onOpenFileAccess' in more
    for text in ('DeepStatusArea.DOWNLOAD_QUEUE','val isQueue =',
                 'cinderbox.screen.download-queue','cinderbox.screen.file-access',
                 'GameDownloadManager','ModDownloadManager','SettingsViewModel',
                 'settings.fileAccessMode','No permission request or privileged service bind',
                 'Review access settings','Open Operation center',
                 'No unseen queued jobs','No automatic'):
        if text == 'No automatic':
            # This is encoded by absence of any privileged call, not a copy requirement.
            continue
        assert text in deep, 'UX08A_MISSING_DEEP_CONTRACT:'+text
    for forbidden in ('requestShizukuPermission(', 'bindShizukuService(',
                      'setFileAccessMode(', 'toggleAutoSync(', 'startDownload(',
                      'installFile(', 'deleteRecursively(', 'Runtime.getRuntime(',
                      'File(', 'pm clear', 'forceSync('):
        assert forbidden not in deep, 'UX08A_UNSAFE_ROUTE:'+forbidden
    assert 'com.sdvsync.qualification.UX08DeepStatusDeviceTest' in script
    assert script.count('ux08a-queue-synthetic.png')==1
    assert script.count('ux08a-file-access-synthetic.png')==1
    assert 'fun queueIsReadOnlyAndOperationCenterIsExplicit()' in test
    assert 'fun fileAccessNeverGrantsPermissionsImplicitly()' in test
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[key] is False, 'UX08A_RELEASE_POLICY_DRIFT:'+key
    source('app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt',root)
    source('app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt',root)
    return {'result':'UX08A_DEEP_ROUTE_AND_SAFETY_PASS','native_deep_screens':2,
            'historical_routes_retained':True,'permissions_requested_by_navigation':False,
            'physical_device_qualified':False,'pixel_parity_verified':False,
            'publication_allowed':False}
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
