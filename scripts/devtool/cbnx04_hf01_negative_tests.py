#!/usr/bin/env python3
"""Run real CB-NX03 receipt parser on synthetic 7-method instrumentation and stage failures."""
import json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'scripts/devtool/cbnx03_instrumentation_receipt.py'
text=path.read_text()
methods=tuple(re.findall(r"    '([A-Za-z0-9_]+)',", text.split('methods = (',1)[1].split(')',1)[0]))
assert len(methods)==7
cls='com.sdvsync.mods.CbNx03PairingDeviceTest'
def event(name,code):
    return f'INSTRUMENTATION_STATUS: class={cls}\nINSTRUMENTATION_STATUS: test={name}\nINSTRUMENTATION_STATUS: numtests=7\nINSTRUMENTATION_STATUS_CODE: {code}\n'
raw=''.join(event(name,'1')+event(name,'0') for name in methods)+'OK (7 tests)\nINSTRUMENTATION_CODE: -1\n'
def probe(raw):
    with tempfile.TemporaryDirectory() as d:
        a=Path(d)
        (a/'raw').write_text(raw)
        proc=subprocess.run([sys.executable,'-B',str(path),'--log',str(a/'raw'),'--exit','0',
            '--source','a'*40,'--run','synthetic','--app-sha','b'*64,'--test-sha','c'*64,
            '--output',str(a/'receipt.json')],capture_output=True,text=True)
        return proc.returncode,json.loads((a/'receipt.json').read_text()),proc.stdout+proc.stderr
rc,receipt,_=probe(raw)
assert rc==0 and receipt['status']=='PASS' and receipt['test_count']==7
assert receipt['safe_pairing_failure_stage'] is None
privacy='SUPER_SECRET_NXM_BEARER_SHOULD_NOT_LEAK'
for stage in ('START','PAIR','STATE_FETCH','STATE_ASSERT','NONCE_REPLAY','NO_INSTALL_ENDPOINT'):
    broken=raw.replace(event('pairingReadOnlyAndNonceReplayFails','0'),
        'INSTRUMENTATION_STATUS: stack=java.lang.AssertionError: CBNX03_SAFE_STAGE_'+stage+' '+privacy+'\n'+
        event('pairingReadOnlyAndNonceReplayFails','-2'),1).replace('OK (7 tests)','FAILURES!!!')
    code,rec,output=probe(broken)
    assert code!=0 and rec['status']=='FAIL' and rec['safe_pairing_failure_stage']==stage,stage
    assert privacy not in json.dumps(rec)+output
for bad in (
    raw.replace('OK (7 tests)','FAILURES!!!'),
    raw.replace('INSTRUMENTATION_STATUS_CODE: 0','INSTRUMENTATION_STATUS_CODE: -2',1),
    raw.replace('INSTRUMENTATION_STATUS_CODE: 1','INSTRUMENTATION_STATUS_CODE: 0',1),
    raw.replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: 0'),
):
    code,rec,_=probe(bad)
    assert code!=0 and rec['status']=='FAIL' and rec['test_count']==0
print('CBNX04B_PAIRING_RECEIPT_NEGATIVE_PASS staged=6 mutants=4 privacy=PASS')

# CB-NX04B migration: this regression check must track the CURRENT canonical
# archive-provenance authority suite; no obsolete seven-method authority contract.
authority_receipt = (ROOT/'scripts/devtool/cbnx04_instrumentation_receipt.py').read_text()
authority_source = (ROOT/'app/src/main/java/com/sdvsync/mods/NexusPairingAuthority.kt').read_text()
archive_source = (ROOT/'app/src/main/java/com/sdvsync/mods/NexusArchiveProvenance.kt').read_text()
assert 'CBNX04B_API36_SYNTHETIC_ARCHIVE_EVIDENCE' in authority_receipt
assert 'method_events != 20' in authority_receipt
assert "'test_count': 10 if ok else 0" in authority_receipt
assert '.put("archive_checksum_qualified", verified)' in authority_source
assert 'NexusArchiveProvenance.inspect(records, privateReviewRoot)' in authority_source
assert 'MessageDigest.getInstance("SHA-256")' in archive_source
assert 'record.modId != mod || record.fileId != file' in archive_source
assert 'method_events != 14' not in authority_receipt
print('CBNX04B_MIGRATED_HF01_NEGATIVE_TESTS_CANONICAL_PASS')
