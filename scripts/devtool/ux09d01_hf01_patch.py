#!/usr/bin/env python3
"""UX09D01 HF01. Exact-source pinned compatibility fixes; no production code.

Applies three *test/gate* corrections only after checking Git blob preimages.
Refuses reapplication and unexpected or dirty source. No Gradle or network.
"""
from __future__ import annotations
import argparse
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HEAD = '724b2c0a41a249089531c84c15c8e6674a55958f'
TREE = 'a90d9ccee0a0a937738e387b20b7823455cd460c'
PREIMAGES = {
 'scripts/devtool/ux_05_mods_gate.py': '6b41165d9a09216c3e7aa2d4058c5ae008cc6924',
 'app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt': '5d80a4f7e7fb9e478c24c68e093b3286de7840c1',
 'scripts/devtool/ux09b4_visual_audit.py': '92257013b34ef5664345e25c21223a395f4db891',
}


def replace_once(text: str, old: str, new: str, rel: str) -> str:
 count = text.count(old)
 assert count == 1, f'UX09D01_HF01_PREIMAGE_MISMATCH:{rel}:{count}:{old[:48]!r}'
 assert old != new
 return text.replace(old, new, 1)


def patch_source(rel: str, old: str) -> str:
 t = old
 if rel == 'scripts/devtool/ux_05_mods_gate.py':
  t = replace_once(t, "for label in ('Your mods','Discover','Installed','Updates','Profiles',", "for label in ('Mods','Discover','Installed','Updates','Profiles',", rel)
  t = replace_once(t, "'Manage profiles','Open advanced manager'):", "'Manage profiles','Manage local mods'):", rel)
  t = replace_once(t, '    for marker in (\'ModManagerViewModel = koinViewModel()\',',
'''    # UX09D01: exact visible page title, not an arbitrary occurrence of "Mods".
    assert 'Text("Mods", color = Dark.Ink' in view, 'UX05_MODS_TITLE_MISSING'
    assert 'Text("Manage local mods")' in view, 'UX05_MANAGER_ACTION_MISSING'
    for marker in ('ModManagerViewModel = koinViewModel()',''', rel)
  t = replace_once(t,'assert \'Triple(BottomTab.MODS, "Your mods", "mods")\' in r48',
    'assert \'Triple(BottomTab.MODS, "Discover, organize and customize.", "mods")\' in r48',rel)
  t = replace_once(t,'assert \'rule.onNodeWithText("Your mods").assertExists()\' in r48',
    'assert \'rule.onNodeWithText("Discover, organize and customize.").assertExists()\' in r48',rel)
 elif rel == 'app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt':
  t = replace_once(t, 'Triple(BottomTab.MODS, "Your mods", "mods")',
                   'Triple(BottomTab.MODS, "Discover, organize and customize.", "mods")', rel)
  t = replace_once(t, 'rule.onNodeWithText("Your mods").assertExists()',
                   'rule.onNodeWithText("Discover, organize and customize.").assertExists()',rel)
 elif rel == 'scripts/devtool/ux09b4_visual_audit.py':
  before='''def independent_colors(img:Image.Image) -> int:
    w,h=img.size; colors=set()
    for y in range(h//4,(h*3)//4,23):
        for x in range(w//8,(w*7)//8,23):
            colors.add(img.getpixel((x,y)))
    return len(colors)
'''
  after='''def independent_colors(img:Image.Image) -> int:
    # Cover actual text and cards above/below the old narrow center band.
    # A frame still fails if it lacks visible foreground or diverse pixels.
    w,h=img.size; colors=set(); foreground=0
    for y in range(h//8,(h*7)//8,13):
        for x in range(w//12,(w*11)//12,13):
            r,g,b=img.getpixel((x,y))
            colors.add((r,g,b))
            if max(r,g,b)>115 and min(r,g,b)>70:
                foreground+=1
    assert foreground>=8, 'UX09B4_NO_VISIBLE_FOREGROUND'
    return len(colors)
'''
  t=replace_once(t,before,after,rel)
 else:
  raise AssertionError(f'UX09D01_HF01_UNEXPECTED_PATH:{rel}')
 assert t!=old
 return t


def git(repo: pathlib.Path, *args: str) -> str:
 return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()


def source_check(repo: pathlib.Path) -> dict[str,bytes]:
 assert git(repo,'rev-parse','HEAD') == HEAD, 'UX09D01_HF01_HEAD_MOVED'
 assert git(repo,'rev-parse','HEAD^{tree}') == TREE, 'UX09D01_HF01_TREE_MOVED'
 assert git(repo,'status','--porcelain=v1','--untracked-files=all').strip() != '', 'UX09D01_HF01_PAYLOAD_NOT_PRESENT'
 data={}
 for rel,blob in PREIMAGES.items():
  file=repo/rel
  assert file.is_file() and not file.is_symlink(),f'UX09D01_HF01_MISSING:{rel}'
  observed=git(repo,'hash-object',rel)
  assert observed==blob, f'UX09D01_HF01_BLOB_MISMATCH:{rel}:{observed}'
  content=file.read_text(encoding='utf-8')
  data[rel]=patch_source(rel,content).encode('utf-8')
 return data


def post_check(repo: pathlib.Path) -> None:
 for rel,blob in PREIMAGES.items():
  file=repo/rel
  assert file.is_file() and not file.is_symlink()
  assert git(repo,'hash-object',rel)!=blob, 'UX09D01_HF01_NO_CHANGE:'+rel
  content=file.read_text(encoding='utf-8')
  assert rel not in PREIMAGES or rel in PREIMAGES
  if rel.endswith('ux_05_mods_gate.py'):
   assert "for label in ('Mods','Discover'" in content
   assert "'Manage profiles','Manage local mods'" in content
   assert 'UX05_MODS_TITLE_MISSING' in content
  elif rel.endswith('R48RealActivityDeviceTest.kt'):
   assert '"Your mods"' not in content
   assert content.count('"Discover, organize and customize."')>=2
  else:
   assert 'UX09B4_NO_VISIBLE_FOREGROUND' in content
   assert 'foreground>=8' in content
 print('UX09D01_HF01_THREE_EXACT_COMPATIBILITY_FIXES_PASS')


def main() -> None:
 p=argparse.ArgumentParser();p.add_argument('--repo',type=pathlib.Path,default=ROOT)
 mode=p.add_mutually_exclusive_group(required=True)
 mode.add_argument('--source-check',action='store_true')
 mode.add_argument('--apply',action='store_true')
 mode.add_argument('--post-check',action='store_true')
 args=p.parse_args()
 repo=args.repo.resolve()
 if args.post_check:
  post_check(repo);return
 data=source_check(repo)
 if args.source_check:
  print('UX09D01_HF01_SOURCE_PIN_AND_ANCHORS_PASS');return
 for rel,payload in data.items():
  (repo/rel).write_bytes(payload)
 post_check(repo)

if __name__=='__main__':
 try:main()
 except (AssertionError,subprocess.CalledProcessError,FileNotFoundError) as exc:
  print('UX09D01_HF01_REFUSED:',exc,file=sys.stderr)
  sys.exit(2)
