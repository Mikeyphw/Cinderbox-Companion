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


CASES=('syntheticArchivePreviewDoesNotModifyLabMods',
       'labPairingRequiresConsentAndRecordsOnlyExactInboxRequest')

def case_status(raw, exit_code, expected):
    assert expected in CASES
    if len(raw) >= 524288:
        return {'test':expected,'status':'NOT_QUALIFIED','failure_code':'LOG_BUDGET'}
    names=re.findall(r'(?m)^INSTRUMENTATION_STATUS: test=(\w+)\r?$',raw)
    passed=(exit_code==0 and len(names)==2 and names.count(expected)==2 and
            'OK (1 test)' in raw and 'INSTRUMENTATION_CODE: 0' in raw and
            'FAILURES!!!' not in raw and 'INSTRUMENTATION_FAILED' not in raw and
            'INSTRUMENTATION_STATUS_CODE: -2' not in raw and
            'INSTRUMENTATION_STATUS_CODE: -1' not in raw)
    if passed: failure='NONE'
    elif exit_code==124: failure='TEST_TIMEOUT'
    elif 'INSTRUMENTATION_FAILED' in raw: failure='RUNNER_FAILED'
    elif 'FAILURES!!!' in raw or 'INSTRUMENTATION_STATUS_CODE: -2' in raw or 'INSTRUMENTATION_STATUS_CODE: -1' in raw: failure='TEST_ASSERTION_FAILED'
    elif exit_code!=0: failure='COMMAND_FAILED'
    elif len(names)!=2 or names.count(expected)!=2: failure='TEST_EVENTS_MISSING'
    else: failure='TEST_SUMMARY_MISSING'
    return {'test':expected,'status':'PASS' if passed else 'NOT_QUALIFIED','failure_code':failure}

def verify_split(raw_preview, code_preview, raw_pair, code_pair, source, run, apk, test_apk):
    assert re.fullmatch(r'[0-9a-f]{40}',source) and re.fullmatch(r'[0-9a-f]{64}',apk) and re.fullmatch(r'[0-9a-f]{64}',test_apk)
    assert re.fullmatch(r'[0-9]{1,24}',run)
    cases=(case_status(raw_preview,code_preview,CASES[0]),case_status(raw_pair,code_pair,CASES[1]))
    passed=all(c['status']=='PASS' for c in cases)
    return {'schema':'cbnx06-lab03a-emulator-v1','receipt_version':2,
            'status':'PASS' if passed else 'NOT_QUALIFIED','cases':list(cases),
            'tests_passed':sum(c['status']=='PASS' for c in cases),'source_sha':source,'run_id':run,
            'apk_sha256':apk,'test_apk_sha256':test_apk,
            'emulator_only':True,'physical_qualified':False,'live_nexus_qualified':False,
            'production_data_immutability_qualified':False,'release_qualified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--raw-pair',type=Path,required=True);p.add_argument('--exit-pair',type=int,required=True)
    p.add_argument('--exit',type=int,required=True);p.add_argument('--source',required=True)
    p.add_argument('--run',required=True);p.add_argument('--apk',required=True)
    p.add_argument('--test-apk',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=verify_split(a.raw.read_text(errors='replace'),a.exit,
        a.raw_pair.read_text(errors='replace'),a.exit_pair,a.source,a.run,a.apk,a.test_apk)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    for c in data['cases']:
        print('CBNX06_LAB03A_HF02_CASE='+c['test']+' STATUS='+c['status']+' REASON='+c['failure_code'])
    if data['status']!='PASS':sys.exit('CBNX06_LAB03A_EMULATOR_NOT_QUALIFIED')
    print('CBNX06_LAB03A_INSTRUMENTATION_RECEIPT_PASS')
if __name__=='__main__':main()
