#!/usr/bin/env python3
"""UX-06 More source + privileged-action separation gate; host only."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def source(path: str, root: Path = ROOT) -> str:
    f = root / path
    assert f.is_file() and not f.is_symlink(), 'UX06_MISSING_OR_LINKED:' + path
    return f.read_text(encoding='utf-8')

def check(root: Path = ROOT) -> dict:
    view = source('app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt',root)
    main = source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    legacy = source('app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt',root)
    vm = source('app/src/main/java/com/sdvsync/ui/viewmodels/SettingsViewModel.kt',root)
    r48 = source('app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',root)
    device = source('app/src/androidTest/java/com/sdvsync/qualification/UX06MoreDeviceTest.kt',root)
    contract = json.loads(source('design/cinderbox/02_CONTRACT/ux-contract.json',root))
    policy = json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    coordinator = source('app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',root)
    assert contract['reference']['sole_theme']=='dark'
    assert contract['navigation']['global_routes']==['home','game_download','saves','mods','settings']
    assert main.count('composable("settings")')==1
    assert main.count('composable("more_advanced")')==1
    assert main.count('composable("more_help")')==1
    assert main.count('composable("more_about")')==1
    assert main.count('ApprovedMoreScreen(')==1
    assert main.count('SettingsScreen(')==2, 'UX06_PRELOGIN_AND_LEGACY_MUST_REMAIN'
    assert 'onOpenSettings = { parentNavController.navigate("more_advanced") }' in main
    assert 'onConnectSteam = { parentNavController.navigate("login") }' in main
    assert 'onOpenOperationCenter = { parentNavController.navigate("operation_center") }' in main
    assert 'onOpenInstallationHealth = { parentNavController.navigate("installation_health") }' in main
    assert 'Triple(BottomTab.SETTINGS, "Connections, preferences and support.", "more")' in r48
    for label in ('MAKE IT YOURS','More','Connections, preferences and support.',
        'Steam account','Not connected · Local mode','Connect Steam','Color theme','Dark · default',
        'Connections & permissions','Nexus Mods','Shizuku','Root access','File access',
        'Preferences','Notifications','Automatic cloud sync','Help & app',
        'Help & safety','Operation center','Installation health','About Cinderbox','Advanced settings'):
        assert label in view, 'UX06_COPY_MISSING:' + label
    for tag in ('cinderbox.screen.more','cinderbox.more.steam-action','cinderbox.more.nexus',
        'cinderbox.more.root','cinderbox.more.shizuku','cinderbox.more.file-access',
        'cinderbox.more.notifications','cinderbox.more.sync','cinderbox.more.advanced'):
        assert tag in view, 'UX06_SEMANTICS_MISSING:' + tag
    for fragment in ('viewModel.load()', 'state.hasNexusApiKey', 'state.shizukuRunning',
        'state.shizukuPermissionGranted', 'state.hasRoot', 'state.isLoggedIn'):
        assert fragment in view, 'UX06_REAL_STATE_MISSING:' + fragment
    for forbidden in ('setFileAccessMode(', 'requestShizukuPermission(', 'bindShizukuService(',
        'RootFileAccess(', 'startDownload(', 'forceSync(', 'toggleAutoSync(', 'logout(',
        'deleteRecursively(', 'File(', 'Runtime.getRuntime(', 'setContent(', 'pm clear'):
        assert forbidden not in view, 'UX06_LANDING_PRIVILEGED_CALL:' + forbidden
    assert 'viewModel.setFileAccessMode("Root")' in legacy
    assert 'viewModel.requestShizukuPermission()' in legacy
    assert 'NexusApiKeySection(' in legacy and 'safLauncher' in legacy
    assert 'fun load()' in vm and 'val hasNexusApiKey: Boolean' in vm
    assert 'val isLoggedIn: Boolean' in vm
    assert 'UX06MoreDeviceTest' in device and 'offlineMoreRetainsRealStatusSemanticsAndExplicitActions' in device
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[key] is False,'UX06_RELEASE_GATE_CHANGED:' + key
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    return {'result':'UX06_MORE_SOURCE_AND_SECURITY_PASS',
       'single_dark':True,'real_settings_state':True,'steam_optional':True,
       'dangerous_actions_secondary_only':True,'legacy_settings_preserved':True,
       'physical_device_qualified':False,'native_visual_parity_verified':False,
       'release_enabled':False}

if __name__ == '__main__':
    print(json.dumps(check(),sort_keys=True))
