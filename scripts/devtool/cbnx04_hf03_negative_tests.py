#!/usr/bin/env python3
"""Mock runner logs: report safe bind cause only on a failed, allowlisted test."""
from pathlib import Path
import re, json, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[2]
parser=ROOT/'scripts/devtool/cbnx03_instrumentation_receipt.py'
txt=parser.read_text()
methods=re.findall(r"    '([A-Za-z0-9_]+)',", txt.split('methods = (',1)[1].split(')',1)[0])
assert len(methods)==7
cls='com.sdvsync.mods.CbNx03PairingDeviceTest'
def event(name,code,stack=''):
    return (f'INSTRUMENTATION_STATUS: class={cls}\n'
            f'INSTRUMENTATION_STATUS: test={name}\n'
            'INSTRUMENTATION_STATUS: numtests=7\n'
            +(f'INSTRUMENTATION_STATUS: stack={stack}\n' if stack else '')
            +f'INSTRUMENTATION_STATUS_CODE: {code}\n')
good=''.join(event(x,'1')+event(x,'0') for x in methods)+'OK (7 tests)\nINSTRUMENTATION_CODE: -1\n'
secret='PRIVATE_NXM_URL_BEARER_SHOULD_NOT_LEAK'
def probe(log):
    with tempfile.TemporaryDirectory() as d:
        d=Path(d);(d/'raw').write_text(log)
        p=subprocess.run([sys.executable,'-B',str(parser),'--log',str(d/'raw'),
              '--exit','0','--source','a'*40,'--run','synthetic',
              '--app-sha','b'*64,'--test-sha','c'*64,'--output',str(d/'out.json')],
              capture_output=True,text=True)
        return p.returncode,json.loads((d/'out.json').read_text()),p.stdout+p.stderr
rc,rec,_=probe(good)
assert rc==0 and rec['status']=='PASS' and rec['safe_pairing_failure_causes']=={}
method='exactFileHandoffRequiresLocalOptInAndNeverStartsDownload'
causes=('BIND_IN_USE','SOCKET_FAILURE','TIMEOUT','SECURITY',
        'INTERRUPTED','ASSERTION','OTHER')
for cause in causes:
    stack='java.lang.AssertionError: CBNX03_SAFE_STAGE_HANDOFF_START CBNX03_SAFE_CAUSE_'+cause+' '+secret
    broken=good.replace(event(method,'0'),event(method,'-2',stack),1).replace('OK (7 tests)','FAILURES!!!')
    code,result,out=probe(broken)
    assert code!=0 and result['status']=='FAIL'
    assert result['safe_pairing_failure_stage']=='HANDOFF_START'
    assert result['safe_pairing_failure_cause']==cause
    assert result['safe_pairing_failure_causes']=={method:cause}
    assert secret not in json.dumps(result)+out
# A passing event must not smuggle a failure cause into the public receipt.
for forged in (good.replace(event(method,'0'),event(method,'0','CBNX03_SAFE_CAUSE_BIND_IN_USE'),1),
               good.replace(event(method,'0'),event(method,'-2','CBNX03_SAFE_CAUSE_STEAL_ME'),1)
                   .replace('OK (7 tests)','FAILURES!!!')):
    code,result,out=probe(forged)
    assert result['safe_pairing_failure_cause'] is None
    assert result['safe_pairing_failure_causes']=={}
    assert secret not in json.dumps(result)+out
print('CBNX04_HF03_BIND_CAUSE_MUTATIONS_PASS allowed=7 forged=2 privacy=PASS')
