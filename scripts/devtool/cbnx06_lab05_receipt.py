#!/usr/bin/env python3
"""LAB05 strict redacted API36 instrumentation receipt. No raw stack/log persisted."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

CASES = (
 'unpairedConsentRemainsDisabledAfterWindowStart',
 'cancelSyntheticInstallDoesNotWriteModsOrJournal',
 'exactFileCancelKeepsRequestPendingWithoutBrowserLaunch',
 'userConfirmedSyntheticInstallAndRollbackRestoresEmptyLabRoot',
)
SAFE_FRAME = re.compile(r'\b(CbNxLab05UiJourneyTest|NexusLab04SyntheticTransaction|NexusLab03DArchiveStage|NexusPairingPanel|NexusPairingInbox)\.kt:([1-9][0-9]{0,3})\b')

# HF02: map untrusted test log text to a fixed set of safe diagnostic categories.
# Never export exception text, full stack traces, local paths, credentials, or URLs.
SAFE_DIAGNOSTIC_CATEGORIES = (
    ('AndroidComposeTestActivity', 'COMPOSE_HOST_ACTIVITY'),
    ('No activities found to launch', 'COMPOSE_HOST_ACTIVITY'),
    ('Unable to resolve activity', 'COMPOSE_HOST_ACTIVITY'),
    ('ActivityNotFoundException', 'COMPOSE_HOST_ACTIVITY'),
    ('NoComposeHierarchiesFoundException', 'COMPOSE_TREE_ABSENT'),
    ('ComposeTimeoutException', 'COMPOSE_WAIT_TIMEOUT'),
    ('ConditionStillNotSatisfiedException', 'COMPOSE_WAIT_TIMEOUT'),
    ('AssertionFailedError', 'ASSERTION'),
    ('AssertionError', 'ASSERTION'),
    ('IllegalStateException', 'RUNTIME_STATE'),
)

def diagnostic_category(raw:str)->str:
    # Limited to constant markers; ambiguous output is UNKNOWN, never a freeform echo.
    for marker, category in SAFE_DIAGNOSTIC_CATEGORIES:
        if marker in raw[:524288]:
            return category
    return 'UNKNOWN'

def case(name:str, raw:str, exit_code:int)->dict:
    assert name in CASES
    if len(raw)>524288: return {'case':name,'status':'NOT_QUALIFIED','reason':'LOG_BUDGET','site':'UNAVAILABLE','failure_category':'LOG_BUDGET'}
    events=re.findall(r'(?m)^INSTRUMENTATION_STATUS: test=(\w+)\r?$',raw)
    ok=(exit_code==0 and events.count(name)==2 and len(events)==2
        and raw.count('INSTRUMENTATION_STATUS_CODE: 1')==1
        and raw.count('INSTRUMENTATION_STATUS_CODE: 0')==1
        and 'OK (1 test)' in raw and 'INSTRUMENTATION_CODE: -1' in raw
        and 'INSTRUMENTATION_STATUS_CODE: -1' not in raw
        and 'INSTRUMENTATION_STATUS_CODE: -2' not in raw
        and 'FAILURES!!!' not in raw and 'INSTRUMENTATION_FAILED' not in raw)
    if ok: return {'case':name,'status':'PASS','reason':'NONE','site':'NONE','failure_category':'NONE'}
    if exit_code==124: reason='TIMEOUT'
    elif 'INSTRUMENTATION_FAILED' in raw: reason='RUNNER_FAILED'
    elif 'FAILURES!!!' in raw or 'INSTRUMENTATION_STATUS_CODE: -2' in raw: reason='ASSERTION_FAILED'
    elif exit_code!=0: reason='COMMAND_FAILED'
    elif len(events)!=2 or events.count(name)!=2: reason='TEST_EVENTS_MISSING'
    else: reason='TEST_SUMMARY_MISSING'
    pos=raw.find('INSTRUMENTATION_STATUS: stack=')
    match=SAFE_FRAME.search(raw[pos:pos+8192]) if pos>=0 else None
    site=match.group(1)+':'+match.group(2) if match else 'UNAVAILABLE'
    return {'case':name,'status':'NOT_QUALIFIED','reason':reason,'site':site,'failure_category':diagnostic_category(raw)}

def verdict(raws:dict[str,tuple[str,int]],source:str,run:str,apk:str,test_apk:str)->dict:
    assert re.fullmatch('[0-9a-f]{40}',source) and re.fullmatch('[0-9]{1,24}',run)
    assert re.fullmatch('[0-9a-f]{64}',apk) and re.fullmatch('[0-9a-f]{64}',test_apk)
    assert set(raws)==set(CASES)
    results=[case(name,*raws[name]) for name in CASES]
    total=sum(c['status']=='PASS' for c in results)
    return {'schema':'cbnx06-lab05-ui-api36-v1','status':'PASS' if total==len(CASES) else 'NOT_QUALIFIED',
       'source_sha':source,'run_id':run,'apk_sha256':apk,'test_apk_sha256':test_apk,
       'actual_test_count':len(results),'tests_passed':total,'cases':results,
       'emulator_only':True,'physical_qualified':False,'live_iceraven_qualified':False,
       'nexus_file_provenance_verified':False,'production_game_unchanged_proven':False,
       'release_qualified':False}

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument('--raw-dir',type=Path,required=True);p.add_argument('--source',required=True)
    p.add_argument('--run',required=True);p.add_argument('--apk',required=True)
    p.add_argument('--test-apk',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    exits=(a.raw_dir/'exits.tsv').read_text().splitlines()
    assert len(exits)==len(CASES)
    codes={}
    for line in exits:
        parts=line.split(' ')
        assert len(parts)==2 and parts[0] in CASES and parts[0] not in codes
        codes[parts[0]]=int(parts[1])
    assert set(codes)==set(CASES)
    raws={x:((a.raw_dir/(x+'.log')).read_text(errors='replace'),codes[x]) for x in CASES}
    data=verdict(raws,a.source,a.run,a.apk,a.test_apk)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    for item in data['cases']:
        print('CBNX06_LAB05_CASE='+item['case']+' STATUS='+item['status']+' REASON='+item['reason']+' SITE='+item['site']+' CATEGORY='+item['failure_category'])
    print('CBNX06_LAB05_ACTUAL_TESTS='+str(data['actual_test_count'])+' PASS='+str(data['tests_passed']))
    if data['status']!='PASS':sys.exit('CBNX06_LAB05_NOT_QUALIFIED')
    print('CBNX06_LAB05_SHA_BOUND_EMULATOR_ONLY_RECEIPT_PASS')
if __name__=='__main__':main()
