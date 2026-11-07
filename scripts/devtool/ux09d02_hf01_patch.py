#!/usr/bin/env python3
"""UX09D02 HF01: byte-exact fix for one invalid Android Compose test import.

The interaction.assertDoesNotExist() method is a member, not a top-level function.
This modifies androidTest only, never production or UX settings. No Gradle locally.
"""
from __future__ import annotations
import argparse,hashlib,os,pathlib,sys,tempfile
BASE_COMMIT='8f29743fb512c0c7518cc43aa1003a5124b3d028'
BASE_TREE='5f7df681c86ae0e6101cec8d81449b4fce1b924a'
PATH='app/src/androidTest/java/com/sdvsync/ui/ux/Ux09D02RealRouteEvidenceTest.kt'
BEFORE_SHA256='c2eb0720c92181c1ce925b49e0a9ce771f811217b0d7bb1e7549c01e5fb08b5c'
AFTER_SHA256='bebd0952e3cf817c258377672a6292d2f20a245fc491bc1e622a9b98048f8a47'
BEFORE_BLOB='629d06a8450ea01f815d97716bd8962d406649ed'
BAD_IMPORT=b'import androidx.compose.ui.test.assertDoesNotExist\n'

class PreimageMismatch(ValueError): pass

def sha256(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def git_blob(b:bytes)->str: return hashlib.sha1(('blob %d\0'%len(b)).encode()+b).hexdigest()

def transform(data:bytes)->bytes:
    if sha256(data)!=BEFORE_SHA256 or git_blob(data)!=BEFORE_BLOB:
        raise PreimageMismatch('UX09D02_HF01_UNEXPECTED_PREIMAGE')
    if data.count(BAD_IMPORT)!=1:
        raise PreimageMismatch('UX09D02_HF01_EXPECTED_ONE_BAD_IMPORT')
    fixed=data.replace(BAD_IMPORT,b'',1)
    if sha256(fixed)!=AFTER_SHA256 or BAD_IMPORT in fixed:
        raise PreimageMismatch('UX09D02_HF01_POSTIMAGE_CHECK_FAILED')
    return fixed

def check(root:pathlib.Path, allow_patched:bool=False):
    path=root/PATH
    if not path.is_file() or path.is_symlink():
        raise PreimageMismatch('UX09D02_HF01_SOURCE_MISSING_OR_SYMLINK')
    data=path.read_bytes()
    if allow_patched and sha256(data)==AFTER_SHA256:
        return 'patched'
    transform(data)
    return 'original'

def apply(root:pathlib.Path)->None:
    status=check(root,allow_patched=True)
    if status=='patched':
        print('UX09D02_HF01_ALREADY_PATCHED_EXACT_POSTIMAGE');return
    path=root/PATH
    original_stat=path.stat()
    fixed=transform(path.read_bytes())
    fd,temp=tempfile.mkstemp(prefix='.ux09d02-hf01-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(fixed)
            f.flush();os.fsync(f.fileno())
        os.chmod(temp, original_stat.st_mode & 0o777)
        if sha256(path.read_bytes())!=BEFORE_SHA256:
            raise PreimageMismatch('UX09D02_HF01_PREIMAGE_CHANGED_BEFORE_WRITE')
        os.replace(temp,path)
        assert check(root,allow_patched=True)=='patched'
    finally:
        if os.path.exists(temp): os.unlink(temp)
    print('UX09D02_HF01_EXACT_TEST_IMPORT_REPAIR_APPLIED')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=pathlib.Path,default=pathlib.Path('.'))
    gr=ap.add_mutually_exclusive_group(required=True)
    gr.add_argument('--source-check',action='store_true')
    gr.add_argument('--post-check',action='store_true')
    gr.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    try:
        if args.source_check:
            assert check(args.repo)=='original'
            print('UX09D02_HF01_EXACT_PREIMAGE_PASS')
        elif args.post_check:
            assert check(args.repo,allow_patched=True)=='patched'
            print('UX09D02_HF01_EXACT_POSTIMAGE_PASS')
        else:apply(args.repo)
    except (AssertionError,PreimageMismatch) as e:
        sys.exit('UX09D02_HF01_REFUSED:'+str(e))
