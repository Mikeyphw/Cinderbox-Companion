#!/usr/bin/env python3
"""Independent, source-bound R2 test and private PNG evidence verifier."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
from m25_emulator_ci import validate_identity
from m25_r2_emulator_ci import TEST_CLASS,TESTS,PNG,RECEIPT,accepted
from r47_capture import png_dimensions

def verify(folder:Path,identity_path:Path,sha:str,run_id:str)->dict:
    assert re.fullmatch('[0-9a-f]{40}',sha) and re.fullmatch('[0-9]+',run_id)
    receipt_file=folder/RECEIPT
    assert receipt_file.is_file() and not receipt_file.is_symlink()
    assert receipt_file.stat().st_size<16000
    result=json.loads(receipt_file.read_bytes())
    expected={
        'schema_version':1,'producer':'cinderbox-m25-r2-hosted-ui',
        'overall':'PASS_M25_R2_HOSTED_EMULATOR','source_sha':sha,'run_id':run_id,
        'test_class':TEST_CLASS,'test_count':len(TESTS),'android_api':36,
        'hosted_emulator_only':True,'physical_device_qualified':False,
        'release_qualified':False,'publication_allowed':False,
        'automatic_installation':False,'raw_logs_retained':False,
    }
    assert all(result.get(k)==v and type(result.get(k)) is type(v) for k,v in expected.items())
    assert 'raw_output' not in result and 'log' not in result and 'stacktrace' not in result
    assert isinstance(result.get('summary'),dict) and accepted(result['summary'])
    identity=validate_identity(identity_path,sha)
    assert result.get('app_apk_sha256')==identity['app_apk_sha256']
    assert result.get('android_test_apk_sha256')==identity['android_test_apk_sha256']
    photo=folder/PNG
    assert photo.is_file() and not photo.is_symlink() and photo.stat().st_size<4_000_000
    assert {p.name for p in folder.glob('*.png')}=={PNG}
    raw=photo.read_bytes();w,h=png_dimensions(raw)
    entry=result.get('screenshot')
    assert isinstance(entry,dict)
    assert entry=={'name':PNG,'sha256':hashlib.sha256(raw).hexdigest(),
                   'bytes':len(raw),'width':w,'height':h}
    return {'overall':'PASS_M25_R2_HOSTED_EVIDENCE_VERIFIED','source_sha':sha,
            'run_id':run_id,'tests_verified':len(TESTS),'screenshots_verified':1,
            'release_qualified':False,'physical_device_qualified':False}

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--r48-identity',required=True,type=Path)
    p.add_argument('--source-sha',required=True)
    p.add_argument('--run-id',required=True)
    a=p.parse_args()
    try:print(json.dumps(verify(a.output_dir,a.r48_identity,a.source_sha,a.run_id),sort_keys=True));return 0
    except (OSError,AssertionError,ValueError,KeyError,TypeError):
        print('M25_R2_EVIDENCE_REFUSED',file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
