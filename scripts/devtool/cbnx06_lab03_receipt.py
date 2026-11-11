#!/usr/bin/env python3
"""Record only a bounded, credential-free test verdict; delete raw instrumentation in runner."""
import argparse,json,re,sys
from pathlib import Path

def verify(raw, code, source, run, apk, test_apk):
    assert re.fullmatch(r'[0-9a-f]{40}',source) and re.fullmatch(r'[0-9a-f]{64}',apk) and re.fullmatch(r'[0-9a-f]{64}',test_apk)
    assert re.fullmatch(r'[0-9]{1,24}',run)
    assert len(raw) < 524288, 'INSTRUMENTATION_LOG_BUDGET'
    names=re.findall(r'(?m)^INSTRUMENTATION_STATUS: test=(\w+)\r?$',raw)
    expected={'syntheticArchivePreviewDoesNotModifyLabMods','labPairingRequiresConsentAndRecordsOnlyExactInboxRequest'}
    passed=code==0 and set(names)==expected and len(names)==2*len(expected) and all(names.count(x)==2 for x in expected) and \
        'OK (2 tests)' in raw and 'INSTRUMENTATION_CODE: 0' in raw and \
        'FAILURES!!!' not in raw and 'INSTRUMENTATION_FAILED' not in raw
    return {'schema':'cbnx06-lab03a-emulator-v1','status':'PASS' if passed else 'NOT_QUALIFIED',
            'source_sha':source,'run_id':run,'apk_sha256':apk,'test_apk_sha256':test_apk,
            'emulator_only':True,'tests_passed':2 if passed else 0,
            'physical_qualified':False,'live_nexus_qualified':False,
            'production_data_immutability_qualified':False,'release_qualified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--exit',type=int,required=True);p.add_argument('--source',required=True)
    p.add_argument('--run',required=True);p.add_argument('--apk',required=True)
    p.add_argument('--test-apk',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=verify(a.raw.read_text(errors='replace'),a.exit,a.source,a.run,a.apk,a.test_apk)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    if data['status']!='PASS':sys.exit('CBNX06_LAB03A_EMULATOR_NOT_QUALIFIED')
    print('CBNX06_LAB03A_INSTRUMENTATION_RECEIPT_PASS')
if __name__=='__main__':main()
