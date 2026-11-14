#!/usr/bin/env python3
"""HF02: all three previously unclassified failure methods; no raw secrets in receipts."""
import json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'scripts/devtool/cbnx03_instrumentation_receipt.py'
source=p.read_text()
methods=re.findall(r"    '([A-Za-z0-9_]+)',",source.split('methods = (',1)[1].split(')',1)[0])
assert len(methods)==7
cls='com.sdvsync.mods.CbNx03PairingDeviceTest'
def ev(name,code,extra=''):
    return f'INSTRUMENTATION_STATUS: class={cls}\nINSTRUMENTATION_STATUS: test={name}\nINSTRUMENTATION_STATUS: numtests=7\n'+extra+f'INSTRUMENTATION_STATUS_CODE: {code}\n'
good=''.join(ev(m,'1')+ev(m,'0') for m in methods)+'OK (7 tests)\nINSTRUMENTATION_CODE: -1\n'
secret='SENSITIVE_TOKEN_AND_NXM_LINK_MUST_NEVER_BE_REPRODUCED'
def run(log):
    with tempfile.TemporaryDirectory() as d:
        d=Path(d);(d/'raw').write_text(log)
        proc=subprocess.run([sys.executable,'-B',str(p),'--log',str(d/'raw'),'--exit','0',
            '--source','a'*40,'--run','fake','--app-sha','b'*64,'--test-sha','c'*64,
            '--output',str(d/'receipt')],capture_output=True,text=True)
        return proc.returncode,json.loads((d/'receipt').read_text()),proc.stdout+proc.stderr
assert run(good)[0]==0
stages={
'exactFileHandoffRequiresLocalOptInAndNeverStartsDownload':
  ('HANDOFF_START','HANDOFF_PAIR','HANDOFF_OPT_IN_GUARD','HANDOFF_LOCAL_ENABLE','HANDOFF_ADMISSION','HANDOFF_STATE','HANDOFF_RESOLVE'),
'inboxSurvivesBridgeShutdownWithoutReenqueuingAnything':
  ('INBOX_START','INBOX_PAIR','INBOX_OPT_IN','INBOX_ADMISSION','INBOX_STOP','INBOX_DURABILITY','INBOX_NO_DOWNLOAD'),
'revokeInvalidatesTokenAndStopsListening':
  ('REVOKE_START','REVOKE_PAIR','REVOKE_ACCEPTED','REVOKE_OLD_TOKEN_DENIED','REVOKE_STOP'),
}
n=0
for method,names in stages.items():
    for name in names:
        bad=good.replace(ev(method,'0'),ev(method,'-2',
            'INSTRUMENTATION_STATUS: stack=CBNX03_SAFE_STAGE_'+name+' '+secret+'\n'),1).replace('OK (7 tests)','FAILURES!!!')
        code,rec,stdout=run(bad)
        assert code!=0 and rec['status']=='FAIL' and rec['test_count']==0
        assert rec['test_results'][method]=='FAIL' and rec['safe_pairing_failure_stage']==name
        assert rec['safe_pairing_failure_stages']=={method:name}
        assert secret not in json.dumps(rec)+stdout
        n+=1
# A forged, undeclared method or missing start/end must remain rejected.
for bad in (good.replace('INSTRUMENTATION_STATUS: test='+methods[0],
                         'INSTRUMENTATION_STATUS: test=rogue',1),
            good.replace(ev(methods[1],'0'),'',1),
            good.replace('OK (7 tests)','FAILURES!!!')):
    code,rec,_=run(bad);assert code!=0 and rec['status']=='FAIL'
print('CBNX04B_PAIRING_FAILURE_MUTATIONS_PASS stages='+str(n)+' forged=3 privacy=PASS')

# CB-NX04B migration: this regression check must track the CURRENT canonical
# archive-provenance authority suite; no obsolete seven-method authority contract.
authority_receipt = (ROOT/'scripts/devtool/cbnx04_instrumentation_receipt.py').read_text()
authority_source = (ROOT/'app/src/main/java/com/sdvsync/mods/NexusPairingAuthority.kt').read_text()
archive_source = (ROOT/'app/src/main/java/com/sdvsync/mods/NexusArchiveProvenance.kt').read_text()
assert 'CBNX04D_API36_SYNTHETIC_NATIVE_UPDATES_EVIDENCE' in authority_receipt
assert 'method_events != 36' in authority_receipt
assert "'test_count': 18 if ok else 0" in authority_receipt
assert '.put("archive_checksum_qualified", verified)' in authority_source
assert 'NexusArchiveProvenance.inspect(records, privateReviewRoot)' in authority_source
assert 'MessageDigest.getInstance("SHA-256")' in archive_source
assert 'record.modId != mod || record.fileId != file' in archive_source
assert 'method_events != 14' not in authority_receipt
print('CBNX04C_MIGRATED_HF02_NEGATIVE_TESTS_CANONICAL_PASS')

assert "SMAPI_CACHE_FRESH" in (ROOT/"app/src/main/java/com/sdvsync/mods/NexusUpdateEvidence.kt").read_text()
