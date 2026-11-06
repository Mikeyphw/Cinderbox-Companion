#!/usr/bin/env python3
"""UX-08B read-only native SMAPI, recovery, and profile detail source policy."""
from __future__ import annotations
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]

def source(rel:str,root:Path=ROOT)->str:
    f=root/rel
    assert f.is_file() and not f.is_symlink(), 'UX08B_MISSING_OR_LINK:'+rel
    return f.read_text(encoding='utf8')

def check(root:Path=ROOT)->dict:
    main=source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    screen=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedDeepToolsScreen.kt',root)
    game=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt',root)
    mods=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt',root)
    profile=source('app/src/main/java/com/sdvsync/mods/models/ModProfile.kt',root)
    legacy_game=source('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt',root)
    legacy_mods=source('app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt',root)
    device=source('app/src/androidTest/java/com/sdvsync/qualification/UX08BDeepToolsDeviceTest.kt',root)
    emulator=source('scripts/devtool/ux08b_emulator_ci.sh',root)
    workflow=source('.github/workflows/cinderbox-ux08b-deep-tools.yml',root)
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    token=source('app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',root)
    contract=json.loads(source('design/cinderbox/02_CONTRACT/ux-contract.json',root))
    assert contract['reference']['sole_theme']=='dark'
    assert contract['navigation']['global_routes']==['home','game_download','saves','mods','settings']
    for route in ('smapi_overview','recovery_overview'):
        assert main.count('composable("'+route+'")')==1,'UX08B_ROUTE:'+route
    assert main.count('route = "profile_detail/{profileId}"')==1
    assert main.count('composable("download_queue")')==1
    assert main.count('composable("file_access_overview")')==1
    assert 'navArgument("profileId") { type = NavType.StringType }' in main
    assert 'Uri.encode(profileId)' in main or 'Uri.encode(id)' in main
    for key in ('ApprovedGameDeepScreen(', 'ApprovedProfileDetailScreen(',
                'onOpenSmapi = { parentNavController.navigate("smapi_overview") }',
                'onOpenRecovery = { parentNavController.navigate("recovery_overview") }',
                'onOpenProfileDetail = { profileId ->'):
        assert key in main,'UX08B_ROUTE_LINK_MISSING:'+key
    assert 'GameSmallAction("Check modding setup", onOpenSmapi' in game
    assert 'GameSmallAction("View setup & recovery", onOpenRecovery' in game
    assert 'GameSmallAction("Advanced game setup", onOpenGameSetup' in game
    assert 'onClick = { onOpenProfileDetail(profile.id) }' in mods
    assert 'onOpenAdvancedMods' in mods
    assert 'val id: String =' in profile
    for key in ('DeepGameArea','SMAPI','RECOVERY','cinderbox.screen.smapi-overview',
                'cinderbox.screen.recovery-overview','cinderbox.screen.profile-detail',
                'state.primarySmapiStatus.name','state.hasRecoverableDownload',
                'state.protectedUpdateStatus','state.profiles.filter { it.id == profileId }',
                'matches.singleOrNull()','profile.isProtected','profile.enabledModIds',
                'Matches observed enabled set',
                'onReviewAdvancedManager','Not verified',
                'onReviewAdvancedSetup','onOpenInstallationHealth'):
        assert key in screen,'UX08B_SCREEN_MISSING:'+key
    # A distinct read-only route is no excuse to move privileged actions into views.
    for forbidden in ('startDownload(', 'extractSmapi(', 'applyProfile(',
                      'applyProfileSafely(', 'deleteProfile(', 'startRecovery(',
                      'requestShizukuPermission(', 'bindShizukuService(',
                      'deleteRecursively(', 'Runtime.getRuntime(', 'java.io.File(',
                      'runAsRoot(', 'setFileAccessMode(', '/storage/emulated/0/'):
        assert forbidden not in screen,'UX08B_PRIVILEGED_CALL:'+forbidden
    assert 'fun GameDownloadScreen(' in legacy_game
    assert 'fun ModManagerScreen(' in legacy_mods
    for flag in ('release_enabled','publication_enabled',
                 'automatic_device_install','device_qualification_complete'):
        assert policy[flag] is False,'UX08B_RELEASE_FLAG:'+flag
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in token
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in token
    assert 'class UX08BDeepToolsDeviceTest' in device
    for fragment in ('smapiIsAdvisoryAndReviewOnly','recoveryDoesNotClaimRepair',
                     'profileShowsOnlySyntheticMetadataAndExplicitManagerAction'):
        assert fragment in device
    assert 'UX08B_HOSTED_DEEP_TOOLS_PASS' in emulator
    assert 'ux08b_emulator_ci.sh' in workflow
    assert 'android-emulator-runner@' in workflow
    return {'result':'UX08B_SOURCE_AND_SAFETY_PASS','new_native_screens':3,
        'stable_profile_identity':True,'privileged_writes_from_new_screens':False,
        'android_compatibility_qualified':False,'release_enabled':False}

if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
