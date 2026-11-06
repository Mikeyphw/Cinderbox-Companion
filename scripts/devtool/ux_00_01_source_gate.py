#!/usr/bin/env python3
"""UX-00/01 source contract. Does not claim emulator/physical acceptance."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def read(p):
 f=root/p
 assert f.is_file() and not f.is_symlink(),f'MISSING_OR_LINKED:{p}'
 return f.read_text()
main=read('app/src/main/java/com/sdvsync/MainActivity.kt')
theme=read('app/src/main/java/com/sdvsync/ui/theme/Theme.kt')
home=read('app/src/main/java/com/sdvsync/ui/screens/HomeScreen.kt')
bottom=read('app/src/main/java/com/sdvsync/ui/components/StardewBottomBar.kt')
settings=read('app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt')
launch_theme=read('app/src/main/res/values/themes.xml')
steam=read('app/src/main/java/com/sdvsync/ui/policy/SteamCapabilityGate.kt')
safety=read('app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt')
contract=json.loads(read('design/cinderbox/02_CONTRACT/ux-contract.json'))
policy=json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
assert contract['reference']['sole_theme']=='dark'
assert 'startDestination = "main"' in main and 'startDestination = "home"' in main
assert 'onConnectSteam = { parentNavController.navigate("login") }' in main
assert 'appearance.mode.resolve' not in main and 'SdvSyncTheme {' in main
assert 'CinderboxDarkTokens.colorScheme' in theme and 'LocalAppearanceStyle provides AppearanceStyle.EARTHY' in theme
assert 'Dark · default' in settings
assert 'android:Theme.Material.NoActionBar' in launch_theme and '#101915' in launch_theme
assert 'Theme.Material.Light.NoActionBar' not in launch_theme
assert 'appearanceStore.setStyle(' not in settings and 'appearanceStore.setMode(' not in settings
assert 'isSteamConnected: Boolean = false' in home and 'onConnectSteam: () -> Unit' in home
assert 'welcomeDismissed' in home and 'cinderbox.screen.home' in home
assert all(steam.count(v)>=1 for v in ('SIGN_IN_REQUIRED','ENTITLEMENT_UNVERIFIED','NETWORK_UNAVAILABLE','CLOUD_UNAVAILABLE'))
for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
 assert policy.get(key) is False, 'RELEASE_SAFETY_CHANGED:'+key
assert 'permitsLiveBulkWrite' in safety and ': Boolean = false' in safety,'LIVE_WRITE_GATE_CHANGED'
for tag in contract['ui_semantics']['nav_tags']:
 assert tag in bottom,'NAV_TAG_MISSING:'+tag
assert 'cinderbox.shell.bottomnav' in bottom and 'cinderbox.shell.content' in main
for code in ('onOpenInstallationHealth','onOpenOperationCenter','onOpenSaves','onOpenMods'):
 assert code in home
assert 'object SteamCapabilityGate' in steam
print('UX_00_01_NATIVE_SOURCE_FOUNDATION_PASS (NOT full screenshot/device qualification)')
