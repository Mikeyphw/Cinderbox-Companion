#!/usr/bin/env python3
"""Canonical SDK provisioning negative tests, exercising the real implementation in-process."""
from pathlib import Path
import importlib.util
import contextlib
import io
import os
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'scripts/devtool/cbnx04_sdk_image_recovery.py'
assert HELPER.is_file()
src = HELPER.read_text(encoding='utf8')
for phrase in ('MAX_ATTEMPTS = 3', 'ATTEMPT_TIMEOUT_SECONDS = 360',
               'system-images;android-36;google_apis;x86_64',
               'UNSAFE_SDK_PACKAGE_LINK', 'ANDROID_SDK_ROOT_MISMATCH',
               "installed(root, str(metadir / 'source.properties'))",
               "installed(root, str(metadir / 'package.xml'))"):
    assert phrase in src, 'CBNX04D_SDK_STALE_CONTRACT:' + phrase
spec=importlib.util.spec_from_file_location('sdk_recovery_live_under_test',HELPER)
recovery=importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)
assert recovery.MAX_ATTEMPTS == 3 and len(recovery.PACKAGES)==4

class Exit:
    def __init__(self,code): self.returncode=code

def scenario(mode, expected_success, setup=None):
    with tempfile.TemporaryDirectory(prefix='cbnx04d-sdk-synthetic-') as tmp:
        sdk=Path(tmp)
        counts={}
        if setup: setup(sdk)
        def fake_install(args,check=False,timeout=None):
            assert args[0]=='/fake/sdkmanager' and args[1]=='--install'
            assert len(args)==3 and timeout==360 and check is False
            package=args[2]
            assert package in dict(recovery.PACKAGES)
            counts[package]=counts.get(package,0)+1
            if mode=='always_fail' or (mode=='transient' and
                    package.startswith('system-images;') and counts[package]==1):
                return Exit(1)
            if mode=='no_marker': return Exit(0)
            rel=dict(recovery.PACKAGES)[package]
            target=sdk/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(b'FAKE-SDK-CONTENT-FOR-UNIT-TEST')
            if package.startswith('system-images;') and mode!='no_metadata':
                (target.parent/'source.properties').write_text('test')
                (target.parent/'package.xml').write_text('test')
            return Exit(0)
        stdout=io.StringIO()
        ok=False
        result=''
        with patch.dict(os.environ, {'ANDROID_HOME':str(sdk),'ANDROID_SDK_ROOT':str(sdk)},clear=False),\
             patch.object(recovery.shutil,'which',return_value='/fake/sdkmanager'),\
             patch.object(recovery.subprocess,'run',side_effect=fake_install),\
             patch.object(recovery.time,'sleep',return_value=None),\
             contextlib.redirect_stdout(stdout):
            try:
                recovery.main()
                ok=True
            except (RuntimeError,OSError) as exc:
                result=str(exc)
        assert ok==expected_success,(mode,ok,stdout.getvalue(),result)
        return counts,stdout.getvalue(),result

counts,log,_=scenario('success',True)
assert len(counts)==4 and all(x==1 for x in counts.values())
assert 'EXACT_API36_GOOGLE_APIS_X86_64_READY' in log
counts,log,_=scenario('transient',True)
assert counts['system-images;android-36;google_apis;x86_64']==2
assert 'RETRYABLE_FAILURE' in log
counts,log,reason=scenario('always_fail',False)
assert counts['platforms;android-35']==3 and 'PACKAGE_INSTALL_UNQUALIFIED' in reason
counts,log,reason=scenario('no_marker',False)
assert counts['platforms;android-35']==3
counts,log,reason=scenario('no_metadata',False)
assert counts['system-images;android-36;google_apis;x86_64']==3

def sym(sdk):
    (sdk/'external').mkdir()
    (sdk/'system-images').symlink_to(sdk/'external')
counts,log,reason=scenario('success',False,sym)
assert 'UNSAFE_SDK_PACKAGE_LINK' in reason
assert recovery.installed.__name__=='installed'
with tempfile.TemporaryDirectory() as tmp:
    with patch.dict(os.environ,{'ANDROID_HOME':tmp,'ANDROID_SDK_ROOT':tmp+'/invalid'},clear=False):
        try:recovery.sdk_root()
        except RuntimeError as e:assert 'MISMATCH' in str(e)
        else:raise AssertionError('Incorrect SDK root escaped')
print('CBNX04D_SDK_RECOVERY_NEGATIVE_PASS cases=7 exact_packages=4 fail_closed=YES')
