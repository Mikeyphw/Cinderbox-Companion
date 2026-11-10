#!/usr/bin/env python3
"""CB-NX04A: exact emulator-event receipts and malicious-log mutation smoke tests."""
import json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
receiver=ROOT/'scripts/devtool/cbnx04_instrumentation_receipt.py'
text=receiver.read_text(encoding='utf8')
names=tuple(re.findall(r"    '([A-Za-z0-9_]+)',",text.split('methods = (',1)[1].split(')',1)[0]))
assert len(names)==7 and len(set(names))==7
sha='a'*40; apk='b'*64

def run(log, exit_code=0, src=sha):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); (root/'raw').write_text(log,encoding='utf8')
        output=root/'STATUS.json'
        result=subprocess.run([sys.executable,'-B',str(receiver), '--log',str(root/'raw'),
            '--exit',str(exit_code),'--source',src,'--run','test-run',
            '--app-sha',apk,'--test-sha',apk,'--output',str(output)],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        receipt=json.loads(output.read_text())
        return result.returncode,receipt,result.stdout+result.stderr

def block(name,code,cls='com.sdvsync.mods.CbNx04AuthorityDeviceTest',total='7'):
    return '\n'.join([f'INSTRUMENTATION_STATUS: class={cls}',
                      f'INSTRUMENTATION_STATUS: test={name}',
                      f'INSTRUMENTATION_STATUS: numtests={total}',
                      f'INSTRUMENTATION_STATUS_CODE: {code}'])+'\n'
raw=''.join(block(name,'1')+block(name,'0') for name in names)
raw+='OK (7 tests)\nINSTRUMENTATION_CODE: -1\n'
rc,receipt,output=run(raw)
assert rc==0 and receipt['status']=='PASS' and receipt['test_count']==7
assert receipt['event_count']==14 and receipt['physical_device_qualified'] is False
mutants=[
    (raw.replace('numtests=7','numtests=8',1),0,sha),
    (raw.replace('com.sdvsync.mods.CbNx04AuthorityDeviceTest','wrong.Class',1),0,sha),
    (raw.replace('INSTRUMENTATION_STATUS_CODE: 0','INSTRUMENTATION_STATUS_CODE: -2',1),0,sha),
    (raw.replace('INSTRUMENTATION_STATUS_CODE: 1','INSTRUMENTATION_STATUS_CODE: 0',1),0,sha),
    (raw.replace('OK (7 tests)','OK (6 tests)'),0,sha),
    (raw.replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: 0'),0,sha),
    (raw,1,sha),
    (raw,0,'not-a-sha'),
    (raw.replace(names[0], 'unknownMethod', 1),0,sha),
    (raw.replace('INSTRUMENTATION_STATUS_CODE: 0\n','',1),0,sha),
    (raw+'FAILURES!!!\n',0,sha),
    (raw.replace('INSTRUMENTATION_STATUS_CODE: 1','INSTRUMENTATION_STATUS_CODE: 1\nINSTRUMENTATION_STATUS_CODE: 1',1),0,sha),
]
for index, (bad,exit_code,source) in enumerate(mutants):
    result,receipt,err=run(bad,exit_code,source)
    assert result and receipt['status']=='FAIL' and receipt['test_count']==0, (index,result,receipt)
    assert receipt['failure_reason_codes'], 'Silent failed receipt'
# A credential-bearing raw error remains exclusively in temporary local logs.
secret='NXM_BEARER_SECRET_SHOULD_NOT_APPEAR'
_,receipt,output=run(raw+'FAILURES!!! '+secret+'\n')
assert secret not in json.dumps(receipt)+output
print('CBNX04_NEGATIVE_AND_PRIVACY_PASS mutations='+str(len(mutants)))
