#!/usr/bin/env python3
"""UX-09A: fail-closed approved native parity source and safety contract.

This validates source and Android-test coverage, not pixel parity, TalkBack,
real-account, entitlement or physical device acceptance.
"""
from __future__ import annotations
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

UI={
 'app/src/main/java/com/sdvsync/ui/screens/HomeScreen.kt':('cinderbox.screen.home','cinderbox.steam.connect','cinderbox.steam.connection-status'),
 'app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt':('cinderbox.screen.game','cinderbox.game.download-action'),
 'app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt':('cinderbox.screen.saves','cinderbox.saves.cloud-pane'),
 'app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt':('cinderbox.screen.mods','cinderbox.mods.discover','cinderbox.mods.installed','cinderbox.mods.updates','cinderbox.mods.profiles'),
 'app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt':('cinderbox.screen.more',),
 'app/src/main/java/com/sdvsync/ui/components/StardewBottomBar.kt':(
    'cinderbox.nav.home','cinderbox.nav.game','cinderbox.nav.saves','cinderbox.nav.mods','cinderbox.nav.more','cinderbox.shell.bottomnav'),
 'app/src/main/java/com/sdvsync/MainActivity.kt':('cinderbox.shell.topbar','cinderbox.shell.content'),
}
TEST='app/src/androidTest/java/com/sdvsync/ui/ux/UxReferenceParityTest.kt'
NAMES=('darkDefaultHome','optionalSteamFirstLaunch','offlineLocalSavesRemainAvailable',
 'steamDownloadsLockedWithoutAuthentication','steamCloudLockedWithoutAuthentication',
 'modsDiscoverAndSections','allFiveBottomTabs','darkThemeTokenParity','backNavigationAndSheets')

def read(root:Path,rel:str)->str:
 p=root/rel
 assert p.is_file() and not p.is_symlink(), 'UX09A_MISSING_OR_SYMLINK:'+rel
 return p.read_text(encoding='utf8')

def check(root:Path=ROOT)->dict:
    root=Path(root)
    contract=json.loads(read(root,'design/cinderbox/02_CONTRACT/ux-contract.json'))
    assert contract['reference']['sole_theme']=='dark', 'UX09A_THEME_DRIFT'
    assert contract['navigation']['global_routes']==['home','game_download','saves','mods','settings'], 'UX09A_ROUTES_DRIFT'
    ui=''; expected=sum((list(values) for values in contract['ui_semantics'].values()),[])
    for path,tags in UI.items():
        src=read(root,path);ui+='\n'+src
        for tag in tags:
            assert ('"'+tag+'"') in src,'UX09A_UI_TAG_MISSING:'+tag
    for tag in expected:
        assert ('"'+tag+'"') in ui, 'UX09A_CONTRACT_SEMANTICS_MISSING:'+tag
    test=read(root,TEST)
    for name in NAMES:
        assert len(re.findall(r'@Test\s+fun\s+'+re.escape(name)+r'\s*\(',test))==1,'UX09A_TEST_MISSING_OR_DUPLICATE:'+name
    for fragment in ('createAndroidComposeRule<MainActivity>()',
                     'cinderbox.screen.home','cinderbox.screen.saves','cinderbox.screen.game',
                     'cinderbox.screen.mods','cinderbox.screen.more','cinderbox.steam.connection-status',
                     'cinderbox.mods.filter','cinderbox.saves.cloud-pane',
                     'Dark.colorScheme.background','captureToImage()',
                     'physical', 'pixel parity'):
        assert fragment.lower() in test.lower(),'UX09A_NATIVE_TEST_MISSING:'+fragment
    assert 'UiReferenceParityTest' not in test, 'UX09A_CLASS_RENAMED'
    assert 'class UxReferenceParityTest' in test
    theme=read(root,'app/src/main/java/com/sdvsync/ui/theme/Theme.kt')
    tokens=read(root,'app/src/main/java/com/sdvsync/ui/theme/CinderboxDarkTokens.kt')
    assert 'CinderboxDarkTokens.colorScheme' in theme
    for name,hexc in contract['dark_palette'].items():
        assert '0xFF'+hexc[1:].upper() in tokens, 'UX09A_DARK_TOKEN_DRIFT:'+name
    main=read(root,'app/src/main/java/com/sdvsync/MainActivity.kt')
    for fragment in ('startDestination = "home"','startDestination = "main"',
        'composable("game_download")','composable("saves")',
        'composable("mods")','composable("settings")'):
        assert fragment in main,'UX09A_NAV_DRIFT:'+fragment
    safety=read(root,'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
    assert 'permitsLiveBulkWrite' in safety and ': Boolean = false' in safety
    policy=json.loads(read(root,'docs/security/M3_RELEASE_POLICY.json'))
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[key] is False,'UX09A_RELEASE_GUARD:'+key
    coordinator=read(root,'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt')
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    wf=read(root,'.github/workflows/cinderbox-ux09a-native-parity.yml')
    for phrase in ('scripts/devtool/ux09a_gate.py','UX09A_HOSTED_PARITY_SEMANTICS_PASS',
                    'api-level: 36','scripts/devtool/ux09a_emulator_ci.sh'):
        assert phrase in (wf+read(root,'scripts/devtool/ux09a_emulator_ci.sh')),'UX09A_HOSTED_CI_MISSING:'+phrase
    for forbidden in ('deleteRecursively(', 'restoreBackup(', 'startDownload(',
      'requestShizukuPermission(', 'setFileAccessMode(', 'forceSync(',
      '/storage/emulated/0/', 'Runtime.getRuntime('):
        assert forbidden not in test,'UX09A_TEST_UNSAFE:'+forbidden
    return dict(result='UX09A_NATIVE_SOURCE_PARITY_PASS',source_only=True,
       required_tags=len(expected),test_scenarios=len(NAMES),full_native_pixel_parity=False,
       real_steam_entitlement_qualified=False,talkback_qualified=False,
       physical_device_qualified=False,release_enabled=False)

if __name__=='__main__':
 try:print(json.dumps(check(),sort_keys=True))
 except (AssertionError,ValueError,OSError,KeyError) as e:
  print('UX09A_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(1)
