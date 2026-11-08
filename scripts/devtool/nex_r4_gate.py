#!/usr/bin/env python3
"""Fail-closed source contract for real offline Saved mod detail; not runtime proof."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCREEN='app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt'
ANDROID='app/src/androidTest/java/com/sdvsync/ui/ux/NexR4OfflineSavedTest.kt'
RUNNER='scripts/devtool/nex_r4_emulator_ci.sh'
EVIDENCE='scripts/devtool/nex_r4_evidence.py'
WORKFLOW='.github/workflows/nex-r4-offline-saved.yml'
DOC='docs/devtool/NEX_R4_OFFLINE_BOOKMARKS.md'
POLICY='docs/security/M3_RELEASE_POLICY.json'

def check(root:Path=ROOT)->list[str]:
    root=Path(root)
    def read(p):
        f=root/p
        if not f.is_file() or f.is_symlink(): raise ValueError('NEX_R4_MISSING_OR_SYMLINK:'+p)
        return f.read_text(encoding='utf-8')
    src=read(SCREEN);android=read(ANDROID);runner=read(RUNNER)
    evidence=read(EVIDENCE);ci=read(WORKFLOW);doc=read(DOC)
    policy=json.loads(read(POLICY))
    required={
      'local saved detail only': all(s in src for s in (
         'val offlineSavedCard = offlineSavedId?.let { savedCards[it] }',
         'if (offlineSavedCard != null && !browse.hasApiKey)',
         'nex.r4.offline-saved-detail', 'nex.r4.offline-title',
         'Saved metadata only. Live details, files and downloads require Nexus access.',
         'onDismissRequest = { offlineSavedId = null }',
         'onClick = { offlineSavedId = null }')),
      'remote detail guarded': all(s in src for s in (
         'if (filter == DiscoverFilter.SAVED && !browse.hasApiKey)',
         'offlineSavedId = id', 'else onOpenRemoteMod(mod.modId, mod.sourceId)',
         'offlineMetadataOnly = filter == DiscoverFilter.SAVED && !browse.hasApiKey')),
      'no offline image HTTP': all(s in src for s in (
         'if (!offlineMetadataOnly && !mod.pictureUrl.isNullOrBlank())',
         'Saved metadata · Available offline')),
      'real activity and isolated fixture': all(s in android for s in (
         'createAndroidComposeRule<MainActivity>()',
         'RuleChain.outerRule(fixture).around(compose)',
         'getNexusApiKey()', 'NEX_R4_REFUSED_EXISTING_BOOKMARKS',
         'NEX_R4_REFUSED_EXISTING_NEXUS_KEY',
         'NEX_R4_REFUSED_UNEXPECTED_NEXUS_REQUEST',
         'NEX_R4_REFUSED_PROVIDER_CALL', 'nexusRequests.get()',
         'NEX_R4_REAL_MAIN_ACTIVITY_SAVED_OFFLINE_PASS')) and
         android.count('NEX_R4_REFUSED_PROVIDER_CALL')>=2,
      'real user journey': all(s in android for s in (
         'BottomTab.MODS.testTag', 'hasText("Saved")',
         'hasText(MOD_NAME)', 'nex.r2.card',
         'nex.r4.offline-saved-detail', 'nex.r4.offline-close',
         'capture("saved-card")', 'capture("offline-sheet")')),
      'offline-only CI and device identity': all(s in runner for s in (
         'GITHUB_ACTIONS', 'ro.kernel.qemu', 'ro.build.version.sdk',
         'r48_offline_gate.py', 'pm clear com.sdvsync',
         'font_scale 1.0', 'NexR4OfflineSavedTest',
         'OK (1 test)', 'NEX_R4_HOSTED_INSTRUMENTATION_REFUSED',
         'nex_r4_evidence.py', 'exec-out run-as')) and
         runner.index('pm clear com.sdvsync') > runner.index('r48_offline_gate.py') and
         runner.count('ro.kernel.qemu')>=2,
      'source-bound evidence': all(s in evidence for s in (
         'STAGES', 'DIMENSIONS', 'hashlib.sha256',
         "'source_sha':source_sha", "'real_device_qualified':False")),
      'hosted real activity CI': all(s in ci for s in (
         'api-level: 36','assembleDebugAndroidTest',
         'nex_r4_gate.py','test_nex_r4_gate.py',
         'test_nex_r4_evidence.py','nex_r4_emulator_ci.sh',
         'nex_r3_gate.py', 'if: always()', 'android-emulator-runner@')),
      'honest scope': all(s in doc.lower() for s in (
         'offline', 'metadata-only', 'synthetic', 'not real nexus',
         'physical-device', 'release')),
    }
    errors=['NEX_R4_MISSING:'+key for key,good in required.items() if not good]
    for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        if policy.get(key) is not False: errors.append('NEX_R4_RELEASE_POLICY_CHANGED:'+key)
    for key in ('CINDERBOX_NEXUS_API_KEY','startDownload(', 'getDownloadUrl(',
                 'installFile(', 'requestShizukuPermission(', 'WebView(', 'Runtime.getRuntime('):
        if key in src+android+runner+ci: errors.append('NEX_R4_UNSAFE:'+key)
    return errors

if __name__=='__main__':
    try: issues=check()
    except (OSError,ValueError,TypeError,KeyError) as exc:raise SystemExit('NEX_R4_GATE_REFUSED:'+str(exc))
    if issues:raise SystemExit('\n'.join(issues))
    print('NEX_R4_OFFLINE_SAVED_SOURCE_AND_SAFETY_PASS')
