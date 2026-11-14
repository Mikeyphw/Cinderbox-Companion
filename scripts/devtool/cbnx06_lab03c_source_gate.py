#!/usr/bin/env python3
"""LAB03C source security policy. Does not qualify live Nexus/browser actions."""
from __future__ import annotations
from pathlib import Path
import re, sys
if sys.flags.optimize: raise SystemExit('LAB03C_ASSERTIONS_REQUIRED')
ROOT=Path(__file__).resolve().parents[2]
class Refused(Exception):pass

def need(yes,reason):
    if not yes: raise Refused('LAB03C_'+reason)

def validate(root=ROOT):
    paths={
      'policy':'app/src/main/java/com/sdvsync/mods/NexusLab03CPolicy.kt',
      'jvm':'app/src/test/java/com/sdvsync/mods/NexusLab03CPolicyTest.kt',
      'panel':'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt',
      'launcher':'app/src/main/java/com/sdvsync/mods/api/NexusBrowserLauncher.kt',
      'inbox':'app/src/main/java/com/sdvsync/mods/NexusPairingInbox.kt',
      'workflow':'.github/workflows/cbnx06-full-cinderbox-lab.yml',
      'hosted':'.github/workflows/cbnx06-lab03c-user-action.yml',
    }
    txt={}
    for key,path in paths.items():
        f=root/path
        need(f.is_file() and not f.is_symlink(),'SOURCE_MISSING_OR_LINKED:'+path)
        txt[key]=f.read_text(encoding='utf8')
    policy,panel,launcher=txt['policy'],txt['panel'],txt['launcher']
    for marker in ('internal object NexusLab03CPolicy',
                   'MAX_REQUEST_AGE_MS = 10 * 60 * 1000L',
                   'Regex("[1-9][0-9]{0,11}")',
                   'if (createdAt <= 0L || now <= 0L || createdAt > now ||',
                   'now - createdAt > MAX_REQUEST_AGE_MS',
                   'return canonicalUrl(modId, fileId)',
                   'https://www.nexusmods.com/stardewvalley/mods/$modId?tab=files&file_id=$fileId'):
        need(marker in policy,'POLICY_ANCHOR_LOST:'+marker)
    for forbidden in ('nxm://','cinderbox_mode=', 'getDownloadUrl(', 'installFromZip(',
                      'startDownload(', 'Authorization:', '/storage/emulated/0/StardewValley'):
        need(forbidden not in policy,'POLICY_PRIVILEGE_LEAK:'+forbidden)
    for marker in ('fun openLabFilePage(context: Context, url: String): Boolean',
                   'if (!BuildConfig.CBNX_LAB || context.packageName != "com.sdvsync.cbnx06lab") return false',
                   'url != NexusLab03CPolicy.canonicalUrl(modId, fileId)',
                   'for (packageName in compatibleBrowserPackages)',
                   '`package` = packageName', 'return true', 'return false'):
        need(marker in launcher, 'LAB_BROWSER_GUARD_MISSING:'+marker)
    launch = launcher.split('fun openLabFilePage(',1)[1]
    need('startActivity(' in launch and launch.count('return true')==1,
         'LAB_BROWSER_LAUNCH_NOT_BOUND_TO_RESULT')
    need('Toast.makeText' not in launch and 'Intent(Intent.ACTION_VIEW, uri)' in launch,
         'LAB_BROWSER_NON_CONSENTED_FALLBACK')
    for marker in ('var lab03cSelection by remember',
                   'lab03cSelection = item // First tap only requests confirmation.',
                   'AlertDialog(', 'cbnx06.lab03c.confirm-open',
                   'cbnx06.lab03c.cancel-open',
                   'cbnx06.lab03c.action-feedback',
                   'NexusPairingInbox.list(context).singleOrNull',
                   'it.fileId == selected.fileId && it.status == "PENDING"',
                   'NexusLab03CPolicy.reviewUrl(',
                   'check(NexusBrowserLauncher.openLabFilePage(context, url))',
                   'check(NexusPairingInbox.resolve(context, current.id, "OPENED"))',
                   'NexusBrowserHandoff.createUrl(item.modId, item.fileId)',
                   'NexusBrowserLauncher.open(context, url)',
                   'Browser launch requested (page unverified)'):
        need(marker in panel,'CONFIRMATION_OR_PRODUCTION_PARITY_LOST:'+marker)
    segment = panel.split('// LAB03C: explicit second tap;',1)[1]
    need(segment.index('NexusPairingInbox.list(context).singleOrNull') <
         segment.index('NexusLab03CPolicy.reviewUrl(') <
         segment.index('NexusBrowserLauncher.openLabFilePage(context, url)') <
         segment.index('NexusPairingInbox.resolve(context, current.id, "OPENED")'),
         'READBACK_CONSENT_LAUNCH_COMMIT_ORDER')
    need('if (BuildConfig.CBNX_LAB) {\n                            lab03cSelection = item' in panel,
         'LAB_SECOND_TAP_NOT_REQUIRED')
    need('if (BuildConfig.CBNX_LAB) {' in panel and
         'else {\n                            // Production keeps its original user-triggered NXM handoff behavior.' in panel,
         'PRODUCTION_NXM_BEHAVIOR_NOT_ISOLATED')
    need('NexusPairingInbox.resolve(context, item.id, "DISMISSED")' in panel,
         'DISMISS_RECOVERY_REMOVED')
    need('fun resolve(context: Context, id: String, status: String): Boolean = synchronized(lock)' in txt['inbox'],
         'PRIVATE_INBOX_NOT_ATOMIC')
    jvm=txt['jvm']
    for name in ('exactBoundedOfficialFilePageHint', 'refusesChangedOrUnverifiedIdentity',
                 'deniesFutureAndExpiredPendingRequests'):
        need('@Test fun '+name in jvm,'JVM_POLICY_TEST_MISSING:'+name)
    for marker in ("      - 'scripts/devtool/cbnx06_lab03c_*.py'",
                   'python3 -B scripts/devtool/cbnx06_lab03c_source_gate.py',
                   'python3 -B scripts/devtool/cbnx06_lab03c_tests.py',
                   ':app:assembleCbnxLab'):
        need(marker in txt['workflow'],'FULL_LAB_WORKFLOW_GATE_MISSING:'+marker)
    for marker in ('scripts/devtool/cbnx06_lab03c_source_gate.py',
                   'scripts/devtool/cbnx06_lab03c_tests.py',
                   ':app:testDebugUnitTest',':app:assembleCbnxLab',
                   'LAB03C_HOSTED_SOURCE_ONLY_NO_PHYSICAL_CLAIM'):
        need(marker in txt['hosted'],'DEDICATED_CI_GATE_MISSING:'+marker)
    print('CBNX06_LAB03C_POLICY_EXACT_FILE_CONSENT_AND_NO_NXM_PASS')

if __name__=='__main__':
    try:validate()
    except (Refused,OSError,ValueError) as e:
        print('CBNX06_LAB03C_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(2)
