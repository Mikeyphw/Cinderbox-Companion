#!/usr/bin/env python3
"""LAB03B UX09: native consent UI stays gated while discoverable before pairing.

Source policy only: hosted Android JVM/emulator and physical observation are independent.
"""
from pathlib import Path
import sys
if sys.flags.optimize: raise SystemExit('LAB03B_UX09_ASSERTIONS_REQUIRED')
ROOT=Path(__file__).resolve().parents[2]
PANEL='app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt'
WORKFLOW='.github/workflows/cbnx06-full-cinderbox-lab.yml'

class Refused(Exception): pass

def verify(s):
    expected=(
        'if (BuildConfig.CBNX_LAB || state.connected)',
        'checked = state.connected && state.handoffEnabled',
        'enabled = state.connected && state.listening',
        'NexusPairingBridge.setHandoffEnabled(it)',
        'if (state.connected && state.listening) {',
        'cbnx03b.pairing.allow-handoff',
        'cbnx06.lab.pairing-status',
        'LAB awaiting Iceraven pairing',
        'Disabled until paired.',
        'LAB paired · enable exact-file requests below.',
        'state.connected && state.handoffEnabled -> "LAB paired',
        'LAB03A synthetic only · Not downloaded from Nexus',
        'NexusPairingInbox.resolve(context, item.id, "OPENED")',
        'NexusPairingInbox.resolve(context, item.id, "DISMISSED")',
    )
    for anchor in expected:
        if anchor not in s: raise Refused('LAB03B_UX09_MISSING_CONTRACT:'+anchor)
    if s.count('NexusPairingBridge.setHandoffEnabled(it)') != 1:
        raise Refused('LAB03B_UX09_DUPLICATE_APPROVAL_SINK')
    if s.count('cbnx03b.pairing.allow-handoff') != 1:
        raise Refused('LAB03B_UX09_DUPLICATE_CONTROLS')
    if s.index('if (BuildConfig.CBNX_LAB || state.connected)') > s.index('LAB03A synthetic only'):
        raise Refused('LAB03B_UX09_SWITCH_BELOW_SYNTHETIC_PREVIEW')
    return True

def check(root=ROOT):
    path=root/PANEL
    if not path.is_file() or path.is_symlink():raise Refused('LAB03B_UX09_MISSING_NATIVE_PANEL')
    verify(path.read_text(encoding='utf-8'))
    w=root/WORKFLOW
    if not w.is_file() or w.is_symlink():raise Refused('LAB03B_UX09_MISSING_WORKFLOW')
    wt=w.read_text(encoding='utf-8')
    for anchor in ('python3 -B scripts/devtool/cbnx06_lab03b_ux09_gate.py',
                   'python3 -B scripts/devtool/cbnx06_lab03b_ux09_tests.py',
                   ':app:assembleCbnxLab'):
        if anchor not in wt:raise Refused('LAB03B_UX09_UNGATED_HOSTED_CI:'+anchor)
    print('LAB03B_UX09_SOURCE_SECURITY_AND_NATIVE_CONSENT_UI_PASS')

if __name__=='__main__':
    try: check()
    except (Refused,OSError,ValueError) as e:
        print('LAB03B_UX09_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(2)
