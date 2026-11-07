#!/usr/bin/env python3
"""UX09C02 HF03: exact-commit, exact-blob host-only instrumentation hardening.

This intentionally modifies no production code or privileged operation gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PINNED_COMMIT='306071d3b139b18653ec1440a0df69fa00b1cd78'
PINNED_TREE='7dc8e891dc1efac8fed1863121bcf7cf65f457c8'
ANDROID_TEST='app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt'
RUNNER='scripts/devtool/ux09c02_emulator_ci.sh'
PREIMAGES={
 ANDROID_TEST:'3dbb3c96a75c26417f67e56d77bd11571646f9da',
 RUNNER:'b8b6fa6cdefd38a316612fe11a538f449c5ccb2f',
}

def once(data:bytes,old:bytes,new:bytes,label:str)->bytes:
 n=data.count(old)
 assert n==1,f'UX09C02_HF03_ANCHOR_COUNT:{label}:{n}'
 return data.replace(old,new,1)

def patch_android(data:bytes)->bytes:
 data=once(data,
  b'import android.content.Context\n',
  b'import android.content.Context\nimport android.os.SystemClock\n',
  'system-clock-import')
 key=b'    @Test fun voluntarySteamConnectionHasClearReturnToApp() {\n'
 helper='''    /**
     * A Steam session-resume transition and NavHost animations can outlive
     * Compose's immediate idle signal, especially after a 200% font change.
     * Await the SAME required semantics (never skip or assume authentication).
     * Named failures keep hosted logs useful without exposing form values.
     */
    private fun requireStage(stage: String, assertion: () -> Unit) {
        val deadline = SystemClock.uptimeMillis() + 12_000L
        var lastFailure: AssertionError? = null
        do {
            rule.waitForIdle()
            try {
                assertion()
                println("UX09C02_STAGE_PASS:" + stage)
                return
            } catch (failure: AssertionError) {
                lastFailure = failure
            }
            SystemClock.sleep(200L)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("UX09C02_STAGE_FAILED:" + stage, lastFailure)
    }

'''
 data=once(data,key,helper.encode()+key,'stage-helper')
 old='''    @Test fun voluntarySteamConnectionHasClearReturnToApp() {
        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        rule.onNodeWithTag("cinderbox.steam-login.screen").assertExists()
        rule.onNodeWithText("Connect your Steam account").assertExists()
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        rule.onNodeWithTag("cinderbox.steam-login.qr").assertExists()
        capture("steam", "cinderbox.steam-login.header")
        rule.onNodeWithTag("cinderbox.steam-login.back").performClick()
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
    }
'''
 new='''    @Test fun voluntarySteamConnectionHasClearReturnToApp() {
        requireStage("home-connect-action") {
            rule.onNodeWithTag("cinderbox.steam.connect").assertExists()
        }
        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        requireStage("steam-screen") {
            rule.onNodeWithTag("cinderbox.steam-login.screen").assertExists()
        }
        requireStage("steam-introduction") {
            rule.onNodeWithText("Connect your Steam account").assertExists()
        }
        // This negative contract remains strict: local mode was already active.
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        requireStage("steam-qr-action") {
            rule.onNodeWithTag("cinderbox.steam-login.qr").assertExists()
        }
        requireStage("steam-header") {
            rule.onNodeWithTag("cinderbox.steam-login.header").assertExists()
        }
        capture("steam", "cinderbox.steam-login.header")
        requireStage("steam-back-action") {
            rule.onNodeWithTag("cinderbox.steam-login.back").assertExists()
        }
        rule.onNodeWithTag("cinderbox.steam-login.back").performClick()
        requireStage("home-after-steam-back") {
            rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        }
    }
'''
 data=once(data,old.encode(),new.encode(),'steam-stage-readiness')
 for token in (b'performScrollToNode(hasTestTag("cinderbox.mods.advanced"))',
               b'capture("steam", "cinderbox.steam-login.header")',
               b'"Continue offline").assertDoesNotExist()',
               b'UX09C02_STAGE_FAILED:',b'SystemClock.sleep(200L)',
               b'voluntarySteamConnectionHasClearReturnToApp'):
  assert token in data, 'UX09C02_HF03_TEST_CONTRACT_DRIFT:'+repr(token)
 assert b'viewModel.login(' not in data, 'UX09C02_HF03_TEST_SIDE_EFFECT'
 return data

def patch_runner(data:bytes)->bytes:
 data=once(data,
  b"grep -E 'FAILURES!!!|Test[s]? run:|Assertion|Exception|Error|INSTRUMENTATION_CODE|UX09C02_' \"$logfile\" | tail -60 >&2 || :",
  b"grep -E 'FAILURES!!!|Test[s]? run:|Assertion|Exception|Error in|INSTRUMENTATION_CODE|UX09C02_STAGE_|UX09C02_' \"$logfile\" | tail -90 >&2 || :",
  'print-stage-markers')
 data=once(data,
  b"r'FAILURES!!!|Tests run:|AssertionError|UX09C02_|INSTRUMENTATION_CODE:'",
  b"r'FAILURES!!!|Tests run:|AssertionError|Error in|UX09C02_STAGE_|UX09C02_|INSTRUMENTATION_CODE:'",
  'sanitized-stage-receipt')
 for token in (b'UX09C02_STAGE_',b'UX09C02_INSTRUMENTATION_REFUSED',b'UX09C02_FAILURE.txt',
               b'UX09C02_PHYSICAL_DEVICE_REFUSED',b'svc wifi disable',b'svc data disable'):
  assert token in data
 return data

def git(root:Path,*args:str)->str:
 return subprocess.check_output(['git',*args],cwd=root,text=True).strip()

def patches(root:Path)->dict[str,bytes]:
 assert git(root,'rev-parse','HEAD')==PINNED_COMMIT,'UX09C02_HF03_HEAD_CHANGED'
 assert git(root,'rev-parse','HEAD^{tree}')==PINNED_TREE,'UX09C02_HF03_TREE_CHANGED'
 out={}
 for name,expected in PREIMAGES.items():
  p=root/name
  assert p.is_file() and not p.is_symlink(),'UX09C02_HF03_SOURCE_MISSING:'+name
  assert git(root,'hash-object',name)==expected,'UX09C02_HF03_PREIMAGE_DRIFT:'+name
  old=p.read_bytes();new=patch_android(old) if name==ANDROID_TEST else patch_runner(old)
  assert new!=old
  out[name]=new
 return out

def apply(root:Path,changes:dict[str,bytes])->None:
 originals={name:(root/name).read_bytes() for name in changes}
 try:
  for name,data in changes.items():(root/name).write_bytes(data)
  for name,data in changes.items():
   assert (root/name).read_bytes()==data,'UX09C02_HF03_POSTIMAGE_DRIFT:'+name
 except BaseException:
  for name,data in originals.items():(root/name).write_bytes(data)
  raise

def main()->None:
 ap=argparse.ArgumentParser()
 ap.add_argument('--repo',required=True,type=Path)
 ap.add_argument('--apply',action='store_true')
 args=ap.parse_args();root=args.repo.resolve()
 changes=patches(root)
 if args.apply:apply(root,changes)
 print(json.dumps({'result':'UX09C02_HF03_NAMED_STAGE_AND_ASYNC_READINESS_PASS',
  'applied':args.apply,'paths':sorted(changes),
  'post_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in changes.items()}},sort_keys=True))

if __name__=='__main__':main()
