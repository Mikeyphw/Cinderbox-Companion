#!/usr/bin/env python3
"""Fail-closed source policy for CB-NX06 full Cinderbox lab build.

Source contract is intentionally narrower than physical qualification: it
rejects unknown direct production-root references and structural regressions.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

if sys.flags.optimize:
    raise SystemExit('CBNX_LAB_GATE_OPTIMIZATION_FORBIDDEN')
ROOT = Path(__file__).resolve().parents[2]
ANDROID = '{http://schemas.android.com/apk/res/android}'
TOOLS = '{http://schemas.android.com/tools}'

class Refused(Exception): pass

def require(cond, message):
    if not cond: raise Refused(message)

def source_without_comments(source: str) -> str:
    """Ignore Kotlin comments without hiding production paths inside string literals.

    Recognizes nested block comments, line comments, escaped regular strings,
    character literals and raw triple-quoted strings. Newlines are preserved.
    """
    output = []
    i = 0
    state = 'code'
    block_depth = 0
    n = len(source)
    while i < n:
        c = source[i]
        pair = source[i:i + 2]
        triple = source[i:i + 3] == '"""'
        if state == 'code':
            if pair == '//':
                output.extend('  '); i += 2; state = 'line'; continue
            if pair == '/*':
                output.extend('  '); i += 2; state = 'block'; block_depth = 1; continue
            if triple:
                output.extend('"""'); i += 3; state = 'raw'; continue
            if c == '"':
                output.append(c); i += 1; state = 'string'; continue
            if c == "'":
                output.append(c); i += 1; state = 'char'; continue
            output.append(c); i += 1; continue
        if state == 'line':
            if c == '\n': output.append(c); state = 'code'
            else: output.append(' ')
            i += 1; continue
        if state == 'block':
            if pair == '/*': output.extend('  '); block_depth += 1; i += 2; continue
            if pair == '*/':
                output.extend('  '); block_depth -= 1; i += 2
                if block_depth == 0: state = 'code'
                continue
            output.append('\n' if c == '\n' else ' '); i += 1; continue
        if state == 'raw':
            if triple: output.extend('"""'); i += 3; state = 'code'; continue
            output.append(c); i += 1; continue
        if c == '\\' and i + 1 < n:
            output.append(source[i:i + 2]); i += 2; continue
        output.append(c)
        if (state == 'string' and c == '"') or (state == 'char' and c == "'"):
            state = 'code'
        i += 1
    require(state not in ('raw', 'string', 'char', 'block'), 'LAB_UNTERMINATED_KOTLIN_SOURCE')
    return ''.join(output)

def check(base: Path = ROOT) -> None:
    app = (base/'app/build.gradle.kts').read_text()
    paths = (base/'app/src/main/java/com/sdvsync/cinderbox/CinderboxPaths.kt').read_text()
    boundary = (base/'app/src/main/java/com/sdvsync/cinderbox/CinderboxLabBoundary.kt').read_text()
    manifest = (base/'app/src/cbnxLab/AndroidManifest.xml').read_text()
    gate = (base/'scripts/devtool/cbnx06_full_lab_gate.py').read_text()
    workflow = (base/'.github/workflows/cbnx06-full-cinderbox-lab.yml').read_text()
    for string in ('create("cbnxLab")', 'applicationIdSuffix = ".cbnx06lab"',
                   'buildConfigField("boolean", "CBNX_LAB", "true")',
                   'signingConfigs.getByName("debug")'):
        require(string in app, 'LAB_GRADLE_BUILD_VARIANT_INCOMPLETE:'+string)
    require('applicationId = "com.sdvsync"' in app and 'getByName("debug")' in app,
            'PRODUCTION_BUILD_CONTRACT_MODIFIED')
    for string in ('CinderboxLabBoundary.root()', 'val ROOT_DIR:',
                   'val MODS_DIR:', 'val SAVES_DIR:', 'val GAME_FILES_DIR:'):
        require(string in paths, 'LAB_PATH_REDIRECT_MISSING:'+string)
    for string in ('com.sdvsync.cbnx06lab', 'context.dataDir.canonicalFile',
                   'context.filesDir.canonicalFile', 'LAB_PATH_ESCAPES_PRIVATE_DATA',
                   'LAB_SYMLINK_REFUSED','requireModsRoot','LAB_MODS_ROOT_MISMATCH',
                   'CBNX06_GAME_LAB', 'files.isDirectory'):
        require(string in boundary, 'LAB_STORAGE_GUARD_MISSING:'+string)
    require('"/storage/emulated/0/StardewValley"' not in paths, 'LAB_PATHS_STILL_HARDCODED')
    root=ET.fromstring(manifest)
    require(root.tag=='manifest', 'LAB_MANIFEST_INVALID_ROOT')
    removed={el.attrib.get(ANDROID+'name') for el in root.findall('uses-permission')
             if el.attrib.get(TOOLS+'node')=='remove'}
    for name in ('MANAGE_EXTERNAL_STORAGE','REQUEST_INSTALL_PACKAGES',
                 'READ_EXTERNAL_STORAGE','WRITE_EXTERNAL_STORAGE'):
        require('android.permission.'+name in removed, 'LAB_PRIVILEGED_PERMISSION_NOT_REMOVED:'+name)
    application=root.find('application')
    require(application is not None, 'LAB_MANIFEST_APPLICATION_MISSING')
    require(application.attrib.get(ANDROID+'label')=='Cinderbox LAB' and
            application.attrib.get(ANDROID+'allowBackup')=='false', 'LAB_UI_OR_BACKUP_IDENTITY_MISSING')
    require(application.attrib.get(TOOLS+'replace')=='android:label',
            'LAB_LABEL_MERGE_PRIORITY_MISSING')
    activity=application.find('activity')
    require(activity is not None and activity.attrib.get(ANDROID+'name')=='.MainActivity'
            and activity.attrib.get(TOOLS+'node')=='replace', 'LAB_ACTIVITY_NOT_REPLACED')
    require(len(activity.findall('intent-filter'))==1, 'LAB_UNEXPECTED_INTENT_FILTERS')
    require('nxm' not in manifest.lower() and 'android.intent.action.VIEW' not in manifest,
            'LAB_NXM_VIEW_INTERCEPTION')
    for component in ('.steam.SteamBackgroundService','.autosync.AutoSyncService',
                      '.download.GameDownloadService','.widget.SyncStatusWidgetReceiver',
                      'rikka.shizuku.ShizukuProvider', 'androidx.core.content.FileProvider'):
        require(any(e.attrib.get(ANDROID+'name')==component and
                    e.attrib.get(TOOLS+'node')=='remove' for e in application.iter()),
                'LAB_PRODUCTION_COMPONENT_NOT_REMOVED:'+component)
    sources={
       'SdvSyncApp.kt':['CinderboxLabBoundary.initialize(this)', 'if (!BuildConfig.CBNX_LAB)'],
       'MainActivity.kt':['if (!BuildConfig.CBNX_LAB) lifecycleScope.launch',
                          'if (BuildConfig.CBNX_LAB && intent.action == Intent.ACTION_VIEW)',
                          'if (BuildConfig.CBNX_LAB) { intent?.data = null; return }'],
       'StoragePreflight.kt':['LAB_STORAGE_OUTSIDE_APP_PRIVATE','CinderboxLabBoundary.isPrivate(destination)'],
       'FileAccessDetector.kt':['if (BuildConfig.CBNX_LAB) return ManualFileAccess()',
                                'if (BuildConfig.CBNX_LAB) return listOf("Manual")',
                                'LAB_CINDERBOX_MODE_CANNOT_BE_DISABLED'],
       'AppModule.kt':['SaveLocation(ManualFileAccess(), CinderboxPaths.SAVES_DIR)'],
       'SaveFileManager.kt':['if (BuildConfig.CBNX_LAB) CinderboxPaths.SAVES_DIR'],
       'GameDownloadManager.kt':['val CINDERBOX_DEST = CinderboxPaths.GAME_FILES_DIR'],
       'ModFileManager.kt':['CinderboxLabBoundary.requireModsRoot(modsDir)'],
       'NexusPairingBridge.kt':['val ACTIVE_PORT: Int get() = if (BuildConfig.CBNX_LAB) 38472 else PORT',
                                'headers["host"] != "127.0.0.1:$ACTIVE_PORT"'],
       'NexusPairingPanel.kt':['ISOLATED LAB (127.0.0.1:38472)'],
    }
    kotlin=base/'app/src/main/java/com/sdvsync'
    for filename, tokens in sources.items():
        files=list(kotlin.rglob(filename))
        require(len(files)==1, 'LAB_SOURCE_UNAVAILABLE_OR_AMBIGUOUS:'+filename)
        txt=files[0].read_text()
        for token in tokens:
            require(token in txt, 'LAB_GUARD_MISSING:'+filename+':'+token)
    production_bind = 'candidate.bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)'
    require(production_bind in (kotlin/'mods/NexusPairingBridge.kt').read_text(),
            'LAB_PRODUCTION_LOOPBACK_BIND_CONTRACT_MISSING')
    # Transitive audit: any NEW absolute production root is a STOP, not an
    # invitation to silently allowlist it. Existing production literal is only
    # reachable through branch-protected CinderboxLabBoundary/SaveFileManager.
    for file in [*kotlin.rglob('*.kt'), *kotlin.rglob('*.java')]:
        txt=source_without_comments(file.read_text())
        if '/storage/emulated/0/StardewValley' in txt and file.name!='CinderboxLabBoundary.kt':
            raise Refused('LAB_UNCLASSIFIED_PRODUCTION_ROOT:'+str(file.relative_to(base)))
        if '/storage/emulated/0/Android/data/com.chucklefish' in txt and file.name!='SaveFileManager.kt':
            raise Refused('LAB_UNCLASSIFIED_GAME_SAVE_ROOT:'+str(file.relative_to(base)))
        if file.name=='SaveFileManager.kt':
            require('if (BuildConfig.CBNX_LAB) CinderboxPaths.SAVES_DIR else' in txt,
                    'LAB_GAME_SAVE_PATH_NOT_GUARDED')
        if re.search(r'const\s+val\s+\w+\s*=\s*CinderboxPaths\.',txt):
            raise Refused('LAB_COMPILETIME_PATH_REMAINS:'+str(file.relative_to(base)))
    for token in (':app:assembleCbnxLab','cbnx06_full_lab_gate.py',
                  'cbnx06_full_lab_artifact.py','cbnx06-full-cinderbox-lab-apk'):
        require(token in workflow, 'LAB_CI_GUARD_MISSING:'+token)
    require('CBNX_LAB_GATE_OPTIMIZATION_FORBIDDEN' in gate, 'LAB_NEGATIVE_TEST_SEAM_MISSING')
    print('CBNX06_FULL_CINDERBOX_LAB_SOURCE_GATE_PASS')

if __name__ == '__main__':
    try: check()
    except (OSError, Refused, ET.ParseError) as e:
        print('CBNX06_FULL_CINDERBOX_LAB_REFUSED:'+str(e),file=sys.stderr)
        raise SystemExit(2)
