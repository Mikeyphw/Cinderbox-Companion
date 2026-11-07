#!/usr/bin/env python3
"""UX-09C02 source-pinned, assertive UI transformation (no business-layer edits)."""
from __future__ import annotations
import argparse,hashlib,subprocess
from pathlib import Path

BASE='df382200b6741d58ea8c297d76fa4a1420b0bef3'
TREE='cac982de2197f57920f6ba19ef2533fd7e767167'
BLOBS={
 'app/src/main/java/com/sdvsync/MainActivity.kt':'9ec5584e8b5afe156fbc2f1fcd54c135e7025b23',
 'app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt':'73088e2cad65ccbf9fd852e6743dfeb58f4075a5',
 'app/src/main/java/com/sdvsync/ui/screens/ModManagerScreen.kt':'3caf4c7ebce50b4c16b2ed436e977c3addbf0a74',
}

def replace_once(s:str,old:str,new:str,name:str)->str:
    assert s.count(old)==1,f'UX09C02_PREIMAGE_MISMATCH:{name}:found={s.count(old)}'
    return s.replace(old,new,1)

def main_activity(s:str)->str:
    s=replace_once(s,'import androidx.compose.foundation.layout.navigationBars',
        'import androidx.compose.foundation.layout.navigationBars\nimport androidx.compose.foundation.layout.statusBars\nimport androidx.compose.foundation.layout.windowInsetsPadding', 'main.inset-import')
    s=replace_once(s,'    NavHost(\n        navController = navController,\n        startDestination = "main",',
        '    // All navigation destinations, including Steam and Advanced Mods, must respect\n'
        '    // the actual phone status bar on Android edge-to-edge. Consume once here.\n'
        '    NavHost(\n        navController = navController,\n        startDestination = "main",\n'
        '        modifier = Modifier.fillMaxSize()\n'
        '            .windowInsetsPadding(WindowInsets.statusBars)\n'
        '            .consumeWindowInsets(WindowInsets.statusBars),', 'main.navhost-inset')
    s=replace_once(s,'            ModManagerScreen(\n                onBrowseClick = { navController.navigate("mods_browse") },',
        '            ModManagerScreen(\n                onBack = { navController.popBackStack() },\n'
        '                onBrowseClick = { navController.navigate("mods_browse") },','main.advanced-back')
    return s

def login(s:str)->str:
    s=replace_once(s,'import androidx.compose.foundation.Image',
      'import androidx.compose.foundation.Image\nimport androidx.compose.foundation.BorderStroke\nimport androidx.compose.foundation.shape.RoundedCornerShape\nimport androidx.compose.ui.platform.testTag\nimport com.sdvsync.ui.theme.CinderboxDarkTokens as Dark', 'login.import')
    s=replace_once(s,'    Scaffold(\n        topBar = {\n            StardewTopAppBar(title = stringResource(R.string.login_title))\n        }\n    ) { padding ->',
      '    Scaffold(\n        modifier = Modifier.testTag("cinderbox.steam-login.screen"),\n'
      '        containerColor = Dark.Background,\n'
      '        topBar = { CinderboxSteamLoginHeader(onBack = onContinueOffline) }\n'
      '    ) { padding ->','login.header')
    s=replace_once(s,'                .padding(horizontal = 24.dp)\n                .verticalScroll(rememberScrollState()),\n            horizontalAlignment = Alignment.CenterHorizontally,\n            verticalArrangement = Arrangement.Center',
      '                .padding(horizontal = 18.dp, vertical = 18.dp)\n'
      '                .imePadding()\n                .verticalScroll(rememberScrollState()),\n'
      '            horizontalAlignment = Alignment.Start,\n'
      '            verticalArrangement = Arrangement.spacedBy(12.dp)', 'login.layout')
    start=s.index('            Spacer(Modifier.weight(1f))\n\n            Box(')
    stop=s.index('            when (val state = authState)',start)
    hero=s[start:stop]
    assert 'PixelIcon(' in hero and 'SparkleOverlay(' in hero and 'login_brand_tagline' in hero,'UX09C02_LOGIN_HERO_DRIFT'
    s=s[:start]+'            CinderboxSteamLoginIntroduction()\n            Spacer(Modifier.height(8.dp))\n\n'+s[stop:]
    old='''            // An offline launch keeps local saves, backups, mods and settings accessible.
            if (authState !is AuthState.LoggedIn) {
                Spacer(Modifier.height(12.dp))
                StardewOutlinedButton(onClick = onContinueOffline, modifier = Modifier.fillMaxWidth()) {
                    Text("Continue offline")
                }
            }
'''
    s=replace_once(s,old,'','login.remove-confusing-offline')
    s=replace_once(s,'                    Text(stringResource(R.string.settings_title))',
      '                    Text("Connection settings")','login.settings-label')
    s=replace_once(s,'            Spacer(Modifier.weight(1f))\n        }\n    }\n}',
      '            Spacer(Modifier.height(24.dp))\n        }\n    }\n}', 'login.end')
    # The QR/password/2FA state machine, form callbacks and safety checks are retained.
    s=replace_once(s,'    StardewOutlinedButton(\n        onClick = onQRLogin,\n        modifier = Modifier.fillMaxWidth()\n    ) {',
      '    Button(\n        onClick = onQRLogin,\n        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)\n            .testTag("cinderbox.steam-login.qr"),\n        shape = RoundedCornerShape(12.dp)\n    ) {','login.qr-primary')
    # Keep input shapes consistent with approved rounded dark UI, including Steam Guard.
    assert s.count('shape = RectangleShape,')>=3,'UX09C02_LOGIN_INPUTS_DRIFT'
    s=s.replace('shape = RectangleShape,','shape = RoundedCornerShape(12.dp),')
    # Avoid any login credential changes beyond layouts/visuals.
    for token in ('viewModel.login()', 'viewModel.loginWithQR()', 'viewModel.submit2FA()',
                  'viewModel.cancelQRLogin()', 'viewModel.tryResumeSession()', 'AuthState.WaitingFor2FA'):
        assert token in s,f'UX09C02_AUTH_FLOW_DRIFT:{token}'
    return s

def mods(s:str)->str:
    s=replace_once(s,'import androidx.compose.ui.platform.LocalContext',
      'import androidx.compose.ui.platform.LocalContext\nimport androidx.compose.ui.platform.testTag', 'mods.testtag-import')
    s=replace_once(s,'    viewModel: ModManagerViewModel = koinViewModel()\n) {',
      '    viewModel: ModManagerViewModel = koinViewModel(),\n    onBack: () -> Unit = {}\n) {','mods.back-param')
    start=s.index('    Scaffold(\n        topBar = {\n            StardewTopAppBar(')
    stop=s.index('    ) { padding ->\n        PullToRefreshBox(',start)+len('    ) { padding ->')
    old=s[start:stop]
    for token in ('showSnapshots = true','viewModel.checkForUpdates()', 'onBrowseClick', 'importLauncher.launch('):
        assert token in old,f'UX09C02_MODS_TOOLBAR_DRIFT:{token}'
    new='''    Scaffold(
        modifier = Modifier.testTag("cinderbox.screen.advanced-mods"),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CinderboxAdvancedModsHeader(
                onBack = onBack,
                onBackups = { viewModel.refreshSafetyState(); showSnapshots = true },
                onUpdates = { viewModel.checkForUpdates() },
                onBrowse = onBrowseClick,
                onImport = { importLauncher.launch(arrayOf("application/zip", "application/x-zip-compressed")) }
            )
        }
    ) { padding ->'''
    s=s[:start]+new+s[stop:]
    start=s.index('                state.installedMods.isEmpty() -> {')
    stop=s.index('\n                else -> {',start)
    old=s[start:stop]
    profile_start=old.index('                            if (state.profiles.isNotEmpty()) {')
    # Original block is part of the nested Column; preserve complete profile callbacks verbatim.
    profile_end=old.index('\n                        }\n                    }\n                }',profile_start)
    profile=old[profile_start:profile_end]
    assert 'ProfileSection(' in profile and 'onApply = { showApplyProfileConfirm = it }' in profile
    new='''                state.installedMods.isEmpty() -> {
                    Column(
                        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        CinderboxAdvancedModsEmpty(
                            onBrowse = onBrowseClick,
                            onImportZip = { importLauncher.launch(arrayOf("application/zip", "application/x-zip-compressed")) },
                            onImportProfile = { importProfile.launch(arrayOf("application/json", "text/plain")) }
                        )
'''+profile+'''
                    }
                }'''
    s=s[:start]+new+s[stop:]
    for important in ('viewModel::confirmPendingReview', 'viewModel::discardPendingReview',
         'viewModel.restoreRetainedSnapshot', 'viewModel.previewPortableImport',
         'viewModel.importFromUri', 'viewModel.dismissBulkPreview', 'ProfileSection('):
        assert important in s,f'UX09C02_MODS_SAFETY_MISSING:{important}'
    return s

TRANSFORMS={
 list(BLOBS)[0]:main_activity,
 list(BLOBS)[1]:login,
 list(BLOBS)[2]:mods,
}

def apply(repo:Path,write:bool)->dict:
    root=repo.resolve()
    verified={}
    for path,sha in BLOBS.items():
        f=root/path
        assert f.is_file() and not f.is_symlink(),'UX09C02_SOURCE_MISSING:'+path
        blob=subprocess.check_output(['git','hash-object','--',str(f)],cwd=root,text=True).strip()
        assert blob==sha,'UX09C02_SOURCE_BLOB_MISMATCH:'+path
        source=f.read_bytes()
        assert b'\r\n' not in source and source.endswith(b'\n'),'UX09C02_LINE_ENDINGS:'+path
        candidate=TRANSFORMS[path](source.decode('utf-8'))
        assert candidate!=source.decode('utf-8'),'UX09C02_NO_CHANGE:'+path
        verified[path]=(f,candidate)
    if write:
        for f,candidate in verified.values():
            f.write_text(candidate,encoding='utf-8',newline='\n')
    return {p:hashlib.sha256(c.encode('utf-8')).hexdigest() for p,(f,c) in verified.items()}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path('.'))
    parser.add_argument('--apply',action='store_true')
    a=parser.parse_args()
    if a.apply:
        import json
        print('UX09C02_TRANSFORM_APPLIED',json.dumps(apply(a.repo,True),sort_keys=True))
    else:
        print('UX09C02_TRANSFORM_PREFLIGHT',apply(a.repo,False))
