#!/usr/bin/env python3
"""UX09C02: fail-closed source and release gate; no live-device privilege claims."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PROD={
'main':'app/src/main/java/com/sdvsync/MainActivity.kt',
'login':'app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt',
'mods':'app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt',
'chrome':'app/src/main/java/com/sdvsync/ui/screens/AdvancedCinderboxChrome.kt',
'androidtest':'app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt',
'workflow':'.github/workflows/cinderbox-ux09c02-device-chrome.yml',
'runner':'scripts/devtool/ux09c02_emulator_ci.sh',
'report':'scripts/devtool/ux09c02_report.py',
'policy':'docs/security/M3_RELEASE_POLICY.json',
'live':'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',
'contract':'design/cinderbox/02_CONTRACT/ux-contract.json',
}

def check(root:Path=ROOT):
    root=Path(root)
    contents={key:(root/path).read_text() for key,path in PROD.items()}
    main,login,mods,chrome=(contents[x] for x in ('main','login','mods','chrome'))
    assert main.count('.windowInsetsPadding(WindowInsets.statusBars)')==1,'UX09C02_STATUS_INSET_NOT_GLOBAL'
    assert '.consumeWindowInsets(WindowInsets.statusBars)' in main,'UX09C02_DOUBLE_INSET_RISK'
    assert 'modifier = Modifier.fillMaxSize()\n            .windowInsetsPadding' in main
    assert 'onBack = { navController.popBackStack() },\n                onBrowseClick' in main
    assert 'Continue offline' not in login,'UX09C02_CONFUSING_OFFLINE_BUTTON'
    assert 'CinderboxSteamLoginHeader(onBack = onContinueOffline)' in login
    assert 'CinderboxSteamLoginIntroduction()' in login
    assert 'Modifier.testTag("cinderbox.steam-login.screen")' in login
    assert 'RoundedCornerShape(12.dp)' in login and 'CinderboxAdvancedModsHeader(' in mods
    for text in ('viewModel.login()', 'viewModel.loginWithQR()', 'viewModel.submit2FA()',
                 'viewModel.cancelQRLogin()', 'viewModel.tryResumeSession()', 'onOpenSettings'):
        assert text in login,'UX09C02_STEAM_FLOW_LOST:'+text
    for text in ('viewModel::confirmPendingReview','viewModel::discardPendingReview',
                 'viewModel.restoreRetainedSnapshot','viewModel.importFromUri',
                 'viewModel.previewPortableImport','viewModel.dismissBulkPreview'):
        assert text in mods,'UX09C02_MOD_REVIEW_LOST:'+text
    for text in ('onBack = onBack','onBackups = { viewModel.refreshSafetyState(); showSnapshots = true }',
                 'onUpdates = { viewModel.checkForUpdates() }','onBrowse = onBrowseClick',
                 'CinderboxAdvancedModsEmpty(','state.profiles.isNotEmpty()'):
        assert text in mods,'UX09C02_MODS_CALLBACK_MISSING:'+text
    assert 'verticalScroll(rememberScrollState())' in mods
    for tag in ('cinderbox.advanced-mods.header','cinderbox.advanced-mods.back',
                'cinderbox.advanced-mods.empty',
                'cinderbox.steam-login.header','cinderbox.steam-login.back'):
        assert '"'+tag+'"' in chrome,'UX09C02_CHROME_TAG_MISSING:'+tag
    assert 'cinderbox.advanced-mods.action.$key' in chrome and 'CinderboxModsAction("Import ZIP", "import"' in chrome
    for token in ('capture("home"','capture("steam"','capture("mods"',
                  'UX09C02_STATUS_BAR_COLLISION','Continue offline',
                  'cinderbox.mods.advanced','cinderbox.steam-login.back'):
        assert token in contents['androidtest'],'UX09C02_TEST_MISSING:'+token
    for token in ('api-level: 36','if: always()','permissions:\n  contents: read',
                  'ux09c02_emulator_ci.sh','ux09c02_gate.py'):
        assert token in contents['workflow'],'UX09C02_CI_MISSING:'+token
    for token in ('UX09C02_PHYSICAL_DEVICE_REFUSED','settings put system font_scale',
                 'svc wifi disable','svc data disable','UX09C02_INSTRUMENTATION_REFUSED'):
        assert token in contents['runner'],'UX09C02_RUNNER_MISSING:'+token
    for token in ("'native_goldens_approved':False","'physical_device_qualified':False",
                  "'steam_auth_qualified':False","'privileged_writes_qualified':False"):
        assert token in contents['report'],'UX09C02_FALSE_CLAIM:'+token
    policy=json.loads(contents['policy'])
    for flag in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[flag] is False,'UX09C02_POLICY_CHANGE:'+flag
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in contents['live']
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in contents['live']
    contract=json.loads(contents['contract']);reference=root/'design/cinderbox'/contract['reference']['path']
    assert contract['reference']['sole_theme']=='dark' and contract['screenshot_cases']['count']==24
    assert reference.is_file() and hashlib.sha256(reference.read_bytes()).hexdigest()==contract['reference']['sha256'],'UX09C02_REFERENCE_CHANGED'
    return {'result':'UX09C02_STATUS_BAR_AND_ADVANCED_SCREENS_SOURCE_PASS',
            'target_screens':['home','steam-login','advanced-mods'],
            'font_scales':[1.0,2.0],'viewports_dp':[393,360],
            'release_enabled':False,'native_goldens_approved':False,'physical_device_qualified':False}

if __name__=='__main__':
    try:print(json.dumps(check(),sort_keys=True))
    except Exception as e:
        print('UX09C02_SOURCE_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(1)
