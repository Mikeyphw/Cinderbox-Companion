#!/usr/bin/env python3
"""LAB06B strict SHA-bound emulator-only receipt; never export private instrumentation."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

SCHEMA = 'cbnx06-lab06b-negative-matrix-api36-v1'
CASES = (
 'changedArchiveBytesCannotReachMods',
 'forgedNexusProvenanceCannotReachMods',
 'incorrectApprovalKeyCannotReachMods',
 'interruptedIntentRequiresManualReview',
 'completedRollbackCannotReplayOrReinstall',
)
SAFE_FRAME = re.compile(r'\b(CbNxLab06bNegativeDeviceTest|NexusLab04SyntheticTransaction|NexusLab03DArchiveStage|ModFileManager|CinderboxLabBoundary)\.kt:([1-9][0-9]{0,3})\b')

# Only these static diagnostic categories leave the CI private raw log directory.
FAILURE_MARKERS = (
 ('LAB06B_STALE_JOURNAL', 'STALE_TEST_FIXTURE'),
 ('LAB06B_MODS_NOT_EMPTY', 'MODS_ROOT_NOT_EMPTY'),
 ('LAB06B_EXPECTED_REFUSAL', 'EXPECTED_REFUSAL_NOT_OBSERVED'),
 ('No tests found', 'MISSING_TEST'),
 ('INSTRUMENTATION_FAILED', 'RUNNER_FAILED'),
 ('AssertionError', 'ASSERTION'),
 ('IllegalStateException', 'RUNTIME_STATE'),
)

def redacted_category(raw: str) -> str:
    for marker, category in FAILURE_MARKERS:
        if marker in raw[:524288]: return category
    return 'UNKNOWN'

def classify(name: str, raw: str, code: int) -> dict:
    assert name in CASES
    if len(raw) > 524288:
        return {'case':name,'status':'NOT_QUALIFIED','reason':'LOG_BUDGET','site':'UNAVAILABLE','category':'LOG_BUDGET'}
    event = re.findall(r'(?m)^INSTRUMENTATION_STATUS: test=(\w+)\r?$',raw)
    ok = (code == 0 and event.count(name) == 2 and len(event) == 2 and
          raw.count('INSTRUMENTATION_STATUS_CODE: 1') == 1 and
          raw.count('INSTRUMENTATION_STATUS_CODE: 0') == 1 and
          'OK (1 test)' in raw and 'INSTRUMENTATION_CODE: -1' in raw and
          'INSTRUMENTATION_STATUS_CODE: -2' not in raw and
          'INSTRUMENTATION_STATUS_CODE: -1' not in raw and
          'FAILURES!!!' not in raw and 'INSTRUMENTATION_FAILED' not in raw)
    if ok: return {'case':name,'status':'PASS','reason':'NONE','site':'NONE','category':'NONE'}
    if code == 124: reason='TIMEOUT'
    elif 'INSTRUMENTATION_FAILED' in raw: reason='RUNNER_FAILED'
    elif 'FAILURES!!!' in raw or 'INSTRUMENTATION_STATUS_CODE: -2' in raw: reason='ASSERTION_FAILED'
    elif code != 0: reason='COMMAND_FAILED'
    elif len(event)!=2 or event.count(name)!=2: reason='TEST_EVENTS_MISSING'
    else: reason='TEST_SUMMARY_MISSING'
    start=raw.find('INSTRUMENTATION_STATUS: stack=')
    m=SAFE_FRAME.search(raw[start:start+8192]) if start>=0 else None
    site=m.group(1)+':'+m.group(2) if m else 'UNAVAILABLE'
    return {'case':name,'status':'NOT_QUALIFIED','reason':reason,'site':site,
            'category':redacted_category(raw)}

def verdict(raws:dict[str,tuple[str,int]], sha:str,run:str,app:str,test:str)->dict:
    assert re.fullmatch(r'[0-9a-f]{40}',sha)
    assert re.fullmatch(r'[1-9][0-9]{0,23}',run)
    assert re.fullmatch(r'[0-9a-f]{64}',app) and re.fullmatch(r'[0-9a-f]{64}',test)
    assert set(raws)==set(CASES)
    cases=[classify(n,*raws[n]) for n in CASES]
    passed=sum(x['status']=='PASS' for x in cases)
    return {'schema':SCHEMA,'status':'PASS' if passed==len(CASES) else 'NOT_QUALIFIED',
            'source_sha':sha,'run_id':run,'apk_sha256':app,'test_apk_sha256':test,
            'actual_test_count':len(cases),'tests_passed':passed,'cases':cases,
            'emulator_only':True,'physical_qualified':False,'live_iceraven_qualified':False,
            'nexus_file_provenance_verified':False,'production_files_examined':False,
            'release_qualified':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--source',required=True)
    p.add_argument('--run',required=True);p.add_argument('--apk',required=True)
    p.add_argument('--test-apk',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    lines=(a.raw_dir/'exits.tsv').read_text().splitlines()
    assert len(lines)==len(CASES)
    codes={}
    for line in lines:
        parts=line.split(' ')
        assert len(parts)==2 and parts[0] in CASES and parts[0] not in codes
        codes[parts[0]]=int(parts[1])
    assert set(codes)==set(CASES)
    raws={n:((a.raw_dir/(n+'.log')).read_text(errors='replace'),codes[n]) for n in CASES}
    data=verdict(raws,a.source,a.run,a.apk,a.test_apk)
    a.output.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf8')
    for x in data['cases']:
        print('CBNX06_LAB06B_CASE='+x['case']+' STATUS='+x['status']+
              ' REASON='+x['reason']+' SITE='+x['site']+' CATEGORY='+x['category'])
    print('CBNX06_LAB06B_ACTUAL_TESTS='+str(data['actual_test_count'])+
          ' PASS='+str(data['tests_passed']))
    if data['status']!='PASS':raise SystemExit('CBNX06_LAB06B_NOT_QUALIFIED')
    print('CBNX06_LAB06B_FIVE_REAL_NEGATIVE_CASES_PASS_HOSTED_ONLY')

if __name__=='__main__':main()
