#!/usr/bin/env python3
"""UX09C02 HF04: source-pinned test fix for 200% large-text Home CTA.

Only edits the Android instrumentation test and its hosted workflow. Steam auth,
production UI, approved design, storage safety, and release controls are untouched.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path

HEAD_PIN='469e0f61a022d23202f116c91db6a4287def658e'
TREE_PIN='9dc2104c1bc28166352330e4818d0e5e5b0f7550'
ANDROID_TEST='app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt'
WORKFLOW='.github/workflows/cinderbox-ux09c02-device-chrome.yml'
PREIMAGES={
 ANDROID_TEST:'c1c5f595544445c3427d738d850c02c8b5e1d315',
 WORKFLOW:'7db3a0a14ccdcf431df07414f863169a04508db3',
}

def once(data:bytes,old:bytes,new:bytes,label:str)->bytes:
 assert data.count(old)==1,f'UX09C02_HF04_ANCHOR_MISMATCH:{label}:{data.count(old)}'
 assert old!=new,f'UX09C02_HF04_NOOP:{label}'
 return data.replace(old,new,1)

def patch_android(data:bytes)->bytes:
 assert b'import androidx.compose.ui.test.assertIsDisplayed\n' not in data,'UX09C02_HF04_ANCHOR_MISMATCH:already-patched-import'
 assert data.count(b'rule.onNodeWithTag("cinderbox.steam.connect").performClick()')==1,'UX09C02_HF04_ANCHOR_MISMATCH:steam-click-not-unique'
 data=once(data,
  b'import androidx.compose.ui.test.onNodeWithText\n',
  b'import androidx.compose.ui.test.onNodeWithText\n'
  b'import androidx.compose.ui.test.assertIsDisplayed\n'
  b'import androidx.compose.ui.test.performScrollTo\n',
  'compose-visible-scroll-imports')
 old="""        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        requireStage("steam-screen") {"""
 new="""        // Home is a real vertically scrolling screen. At 200% system text,
        // the optional Steam card can be below the visible viewport. Compose
        // can find its semantics node without that node being tappable.
        // Scroll the existing button into view and require actual visibility
        // BEFORE a real click; never navigate directly or fake login state.
        requireStage("home-connect-visible") {
            rule.onNodeWithTag("cinderbox.steam.connect")
                .performScrollTo()
                .assertIsDisplayed()
        }
        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        requireStage("steam-screen") {"""
 data=once(data,old.encode(),new.encode(),'home-cta-scroll-before-tap')
 for token in (b'requireStage("home-connect-action")',
               b'requireStage("home-connect-visible")',
               b'.performScrollTo()\n                .assertIsDisplayed()',
               b'requireStage("steam-screen")',
               b'requireStage("steam-qr-action")',
               b'requireStage("steam-back-action")',
               b'requireStage("home-after-steam-back")',
               b'"Continue offline").assertDoesNotExist()',
               b'capture("steam", "cinderbox.steam-login.header")',
               b'performScrollToNode(hasTestTag("cinderbox.mods.advanced"))'):
  assert token in data,'UX09C02_HF04_REQUIRED_SEMANTIC_LOST:'+repr(token)
 assert data.index(b'.performScrollTo()')<data.index(b'"cinderbox.steam.connect").performClick()')
 return data

def patch_workflow(data:bytes)->bytes:
 assert b'test_ux09c02_hf04_fix.py' not in data,'UX09C02_HF04_ANCHOR_MISMATCH:workflow-already-patched'
 old=b"          python3 -B -m unittest discover -s scripts/devtool -p 'test_ux09c02_gate.py' -v\n"
 new=(old+b"          python3 -B -m unittest discover -s scripts/devtool -p 'test_ux09c02_hf04_fix.py' -v\n")
 data=once(data,old,new,'host-source-regression')
 for marker in (b'hosted-api36-ui:',b':app:assembleDebugAndroidTest',
  b'permissions:\n  contents: read',b'api-level: 36',b'if: always()'):
  assert marker in data,'UX09C02_HF04_CI_GUARD_DRIFT:'+repr(marker)
 return data

def sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def git(root:Path,*args:str)->str:
 return subprocess.check_output(['git',*args],cwd=root,text=True).strip()

def changes(root:Path)->dict[str,bytes]:
 assert git(root,'rev-parse','HEAD')==HEAD_PIN,'UX09C02_HF04_HEAD_DRIFT'
 assert git(root,'rev-parse','HEAD^{tree}')==TREE_PIN,'UX09C02_HF04_TREE_DRIFT'
 # Devtool has already created the three add-only files when its validator
 # invokes this checker. The wrapper enforces the clean worktree BEFORE apply.
 result={}
 for p,expect in PREIMAGES.items():
  file=root/p
  assert file.is_file() and not file.is_symlink(),'UX09C02_HF04_MISSING_SOURCE:'+p
  assert git(root,'hash-object',p)==expect,'UX09C02_HF04_BLOB_DRIFT:'+p
  old=file.read_bytes()
  new=patch_android(old) if p==ANDROID_TEST else patch_workflow(old)
  assert old!=new
  result[p]=new
 return result

def apply(root:Path, result:dict[str,bytes])->None:
 original={p:(root/p).read_bytes() for p in result}
 try:
  for p,data in result.items():(root/p).write_bytes(data)
  for p,data in result.items():
   assert (root/p).read_bytes()==data,'UX09C02_HF04_POSTIMAGE_DRIFT:'+p
 except BaseException:
  for p,data in original.items():(root/p).write_bytes(data)
  raise

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--repo',type=Path,required=True)
 ap.add_argument('--apply',action='store_true')
 args=ap.parse_args()
 root=args.repo.resolve();patched=changes(root)
 if args.apply:apply(root,patched)
 print(json.dumps({'result':'UX09C02_HF04_REAL_VISIBLE_STEAM_CTA_SOURCE_PASS','applied':args.apply,
  'paths':sorted(patched),'post_sha256':{p:sha256(d) for p,d in patched.items()}},sort_keys=True))

if __name__=='__main__':main()
