#!/usr/bin/env python3
"""UX-03 exact native Game route and read-only safety source contract."""
from __future__ import annotations
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]

def source(path: str, root: Path=ROOT) -> str:
    p=root/path
    assert p.is_file() and not p.is_symlink(), 'UX03_MISSING_OR_SYMLINK:'+path
    return p.read_text(encoding='utf-8')

def check(root: Path=ROOT) -> dict:
    game=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt',root)
    main=source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    r48=source('app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt',root)
    legacy=source('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt',root)
    tokens=source('app/src/main/java/com/sdvsync/ui/theme/CinderboxDarkTokens.kt',root)
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    state=source('app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt',root)
    coordinator=source('app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',root)
    contract=json.loads(source('design/cinderbox/02_CONTRACT/ux-contract.json',root))
    assert contract['navigation']['global_routes'][1]=='game_download'
    assert contract['reference'].get('dark_default') is True
    assert main.count('composable("game_download")')==1
    assert main.count('composable("game_setup_advanced")')==1
    assert 'ApprovedGameScreen(' in main and 'isSteamConnected = steamConnection == ConnectionState.LOGGED_IN' in main
    assert 'onOpenGameSetup = { parentNavController.navigate("game_setup_advanced") }' in main
    assert 'onConnectSteam = { parentNavController.navigate("login") }' in main
    assert 'GameDownloadScreen(' in main and 'onBack = { navController.popBackStack() }' in main
    assert 'startDestination = "home"' in main and 'startDestination = "main"' in main
    assert 'cinderbox.screen.game' in game and 'cinderbox.game.download-action' in game
    assert 'cinderbox.game.cover' in game and 'cinderbox.game.activity' in game
    assert 'Stardew Valley' in game and 'Connect Steam to download' in game
    for label in ('Install & download','Modding environment','Storage & recovery','Installation health','Files','Steam game download'):
        assert label in game, 'UX03_MISSING_APPROVED_SECTION:'+label
    assert 'R43DDestinationPresentation.from(' in game
    assert 'R43DDestinationPresentation.installedLabel(' in game
    assert 'state.primaryGameStatus' in game and 'state.primarySmapiStatus' in game
    assert 'GameDownloadViewModel = koinViewModel()' in game and 'LifecycleResumeEffect(viewModel)' in game
    assert 'if (isSteamConnected) onOpenGameSetup else onConnectSteam' in game
    assert 'Steam is connected. Game entitlement, access and storage still require verification.' in game
    assert 'Not verified' in game and 'Not Steam-verified' not in game
    for unsafe in ('File(', 'deleteRecursively(', 'startDownload(', 'onDownloadButtonClicked(',
                   'startProtectedUpdateConfirmed(', 'installPackage(', 'Runtime.getRuntime()',
                   'requestShizukuPermission(', 'pm clear', '/storage/emulated/0/'):
        assert unsafe not in game, 'UX03_UNSAFE_GAME_OVERVIEW:'+unsafe
    assert 'GameDownloadScreen(' in legacy
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[key] is False, 'UX03_RELEASE_SWITCH_ENABLED:'+key
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    assert 'cinderbox.screen.home' in source('app/src/main/java/com/sdvsync/ui/screens/HomeScreen.kt',root)
    assert 'CinderboxDarkTokens.colorScheme' in source('app/src/main/java/com/sdvsync/ui/theme/Theme.kt',root)
    assert 'val Background = Color(0xFF101915)' in tokens
    assert 'Triple(BottomTab.DOWNLOAD, "Stardew Valley", "game")' in r48
    assert 'rule.onNodeWithText("Stardew Valley").assertExists()' in r48
    assert 'primaryGameStatus: M23InstallationDiscovery.Status' in state
    assert 'primarySmapiStatus: M23InstallationDiscovery.Status' in state
    return {'result':'UX03_APPROVED_DARK_GAME_SOURCE_PASS','source_only':True,
            'game_route':'game_download','advanced_route':'game_setup_advanced',
            'no_write_authorization':True,'steam_auth_optional':True,
            'native_screenshot_parity_verified':False,'release_enabled':False}

if __name__=='__main__':
    print(json.dumps(check(),sort_keys=True))
