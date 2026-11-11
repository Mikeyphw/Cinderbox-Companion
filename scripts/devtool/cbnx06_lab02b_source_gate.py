#!/usr/bin/env python3
"""LAB02B: static guard against lab-to-production filesystem and Steam access.

This is a source contract, not an Android runtime safety proof.
Existing LAB02A and CB-NX03/04/06 security gates remain independently required.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys
if sys.flags.optimize:
    raise SystemExit('CBNX06_LAB02B_ASSERTIONS_REQUIRED')
ROOT = Path(__file__).resolve().parents[2]
class Refused(Exception): pass

def require(condition, code):
    if not condition: raise Refused(code)

def validate(root=ROOT):
    prefix='app/src/main/java/com/sdvsync/'
    paths={
        'transport':prefix+'steam/SteamClientManager.kt',
        'auth':prefix+'steam/SteamAuthenticator.kt',
        'settings':prefix+'ui/screens/SettingsScreen.kt',
        'activity':prefix+'MainActivity.kt',
        'manifest':'app/src/cbnxLab/AndroidManifest.xml',
        'workflow':'.github/workflows/cbnx06-full-cinderbox-lab.yml',
    }
    content={}
    for key,path in paths.items():
        file=root/path
        require(file.is_file() and not file.is_symlink(), 'LAB02B_MISSING_OR_LINKED_SOURCE:'+key)
        content[key]=file.read_text(encoding='utf-8')
    # The guard must be an executable statement directly at each entry point,
    # not somewhere else in the file or a comment string.
    transport=content['transport']
    require('import com.sdvsync.BuildConfig' in transport, 'LAB02B_TRANSPORT_BUILD_VARIANT_MISSING')
    require(re.search(r'suspend fun connect\(\) = connectMutex\.withLock \{\s*'
                      r'check\(!BuildConfig\.CBNX_LAB\) \{ "CBNX_LAB_STEAM_TRANSPORT_BLOCKED" \}',transport) is not None,
            'LAB02B_STEAM_CONNECT_GUARD_MISSING')
    require(re.search(r'private fun startConnection\(candidate: ServerRecord\): Boolean = synchronized\(transportLifecycleLock\) \{\s*'
                      r'check\(!BuildConfig\.CBNX_LAB\) \{ "CBNX_LAB_STEAM_TRANSPORT_BLOCKED" \}',transport) is not None,
            'LAB02B_STEAM_CONNECTION_FALLBACK_UNGUARDED')
    auth=content['auth']
    require('import com.sdvsync.BuildConfig' in auth,'LAB02B_AUTH_BUILD_VARIANT_MISSING')
    for anchor in ('suspend fun login(username: String, password: String)',
                   'suspend fun loginWithQR()', 'suspend fun loginWithSavedSession()'):
        require(anchor+' {\n        check(!BuildConfig.CBNX_LAB) { "CBNX_LAB_STEAM_AUTH_FORBIDDEN" }' in auth,
                'LAB02B_STEAM_CREDENTIAL_ENTRY_UNGUARDED:'+anchor)
    for anchor in ('fun onAppForeground()', 'fun onAppBackground()',
                   'private fun requestSavedSessionRecovery(reason: String)'):
        require(anchor+' {\n        if (BuildConfig.CBNX_LAB) return' in auth,
                'LAB02B_STEAM_AUTORECONNECT_UNGUARDED:'+anchor)
    settings=content['settings']
    for marker in ('if (!BuildConfig.CBNX_LAB && confirmRoot)',
                   'if (!BuildConfig.CBNX_LAB && state.showStoragePermissionPrompt)',
                   'if (!BuildConfig.CBNX_LAB && state.allFilesEligible)',
                   'if (!BuildConfig.CBNX_LAB && state.safEligible)',
                   'if (!BuildConfig.CBNX_LAB) {\n                            // Root is never auto-probed.',
                   'if (!BuildConfig.CBNX_LAB) {\n                Spacer(Modifier.height(12.dp))\n                ShizukuStatusSection('):
        require(marker in settings, 'LAB02B_PRIVILEGED_UI_UNGUARDED:'+marker[:66])
    activity=content['activity']
    require('if (BuildConfig.CBNX_LAB) Text(' in activity and
            'cbnx06.lab.persistent-banner' in activity and
            'CINDERBOX LAB - PRIVATE GAME DATA' in activity,
            'LAB02B_PERSISTENT_LAB_IDENTITY_MISSING')
    manifest=content['manifest']
    require('tools:replace="android:label"' in manifest and
            'android:label="Cinderbox LAB"' in manifest and
            'android.permission.MANAGE_EXTERNAL_STORAGE" tools:node="remove"' in manifest and
            '<data android:scheme="nxm"' not in manifest,
            'LAB02B_LAB_MANIFEST_REGRESSION')
    workflow=content['workflow']
    for marker in ('python3 -B scripts/devtool/cbnx06_lab02b_source_gate.py',
                   'python3 -B scripts/devtool/cbnx06_lab02b_tests.py',
                   'scripts/devtool/cbnx06_lab02b_*.py',
                   ':app:assembleCbnxLab'):
        require(marker in workflow,'LAB02B_WORKFLOW_NOT_GATED:'+marker)
    print('CBNX06_LAB02B_SOURCE_SECURITY_GATES_PASS')

if __name__=='__main__':
    try: validate()
    except (Refused,ValueError,OSError) as exc:
        print('CBNX06_LAB02B_REFUSED:'+str(exc),file=sys.stderr)
        raise SystemExit(2)
