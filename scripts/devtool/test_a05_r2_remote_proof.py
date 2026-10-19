"""A05-R2: GitHub omitted inputs and --machine-file EXO payloads, fail closed."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/devtool'))
import a05_actions_qualification as a05

SHA='7675f3471326b3ca52a9474a17d96a6bde2943d6'
RUN=39301086093

def api_objects(mode='native-only',inputs=None):
    run={'id':RUN,'head_sha':SHA,'event':'workflow_dispatch','status':'completed',
         'conclusion':'success','path':a05.WORKFLOW+'@refs/heads/feature/m24-steam-download-safety',
         'run_attempt':1}
    if inputs is not None:run['inputs']=inputs
    jobs={'total_count':2,'jobs':[
        {'name':'A05 native DAG + EXO evidence','status':'completed','conclusion':'success','run_attempt':1},
        {'name':'build-debug-apk','status':'completed',
         'conclusion':'skipped' if mode=='native-only' else 'success','run_attempt':1}]}
    artifacts={'total_count':1,'artifacts':[{'name':a05.ARTIFACT,'id':12211842809,
                'expired':False,'workflow_run':{'id':RUN}}]}
    return run,jobs,artifacts

def machine_outputs(inp):
    for n in ('devtool-plan.json','devtool-preflight.json'):
        (inp/n).write_text(json.dumps({'ok':True,'exit_code':0,'result':{'success':True}}))
    (inp/'devtool-invoke.json').write_text(json.dumps({
        'ok':True,'exit_code':0,'machine':{'operation':{'status':'ok'}},
        'totals':{'failed':0,'errors':0}}))

class R2ProofTests(unittest.TestCase):
    def test_frozen_dispatch_mode_guards_exist_at_source_commit(self):
        # The local synthetic checkout has identical workflow bytes to real A05.
        p=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True,check=True)
        a05._frozen_mode_contract(p.stdout.strip())

    def test_omitted_inputs_native_only_succeeds_with_exact_jobs_and_machine_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/'input';inp.mkdir();machine_outputs(inp)
            source=root/'fixture';a05.record(source,SHA,a05.DEVTOOL_SHA,a05.REPO,RUN,1,inp)
            target=root/'download';run,jobs,artifacts=api_objects()
            def gh_download(cmd,**kwargs):
                self.assertEqual(cmd[:3],['gh','run','download'])
                for path in source.iterdir():shutil.copyfile(path,target/path.name)
                return subprocess.CompletedProcess(cmd,0,'','')
            with patch.object(a05,'_frozen_mode_contract') as frozen:
                with patch.object(a05,'_gh_api',side_effect=[run,jobs,artifacts]):
                    with patch.object(a05.subprocess,'run',side_effect=gh_download):
                        proof=a05.verify_run(RUN,target,SHA,'native-only')
            frozen.assert_called_once_with(SHA)
            self.assertEqual(proof['overall'],'PASS_CINDERBOX_A05_GITHUB_RUN_VERIFIED')
            self.assertEqual(proof['artifact_id'],12211842809)
            self.assertFalse(proof['release_qualified'])
            self.assertFalse(proof['device_qualified'])

    def test_explicit_conflicting_input_still_refused(self):
        run,_,_=api_objects(inputs={'a05_mode':'off'})
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',return_value=run):
                with self.assertRaisesRegex(a05.ProofError,'input mode'):
                    a05.verify_run(RUN,Path(d)/'out',SHA,'native-only')

    def test_omitted_inputs_cannot_claim_native_only_if_build_executed(self):
        run,jobs,_=api_objects(mode='both')
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_frozen_mode_contract'):
                with patch.object(a05,'_gh_api',side_effect=[run,jobs]):
                    with self.assertRaisesRegex(a05.ProofError,'skip Android'):
                        a05.verify_run(RUN,Path(d)/'out',SHA,'native-only')

    def test_omitted_inputs_requires_exact_pinned_workflow_guards(self):
        run,_,_=api_objects()
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',return_value=run):
                with patch.object(a05,'_frozen_mode_contract',side_effect=a05.ProofError('guards tampered')):
                    with self.assertRaisesRegex(a05.ProofError,'guards tampered'):
                        a05.verify_run(RUN,Path(d)/'out',SHA,'native-only')

    def test_machine_file_success_and_failure_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inp=root/'inputs';inp.mkdir();machine_outputs(inp)
            out=root/'out';a05.record(out,SHA,a05.DEVTOOL_SHA,a05.REPO,RUN,1,inp)
            self.assertEqual(a05.verify_local(out,run_id=RUN,attempt=1,source_sha=SHA)['overall'],
                             'PASS_CINDERBOX_A05_LOCAL_EVIDENCE_VERIFIED')
            for variant in ['failed_status','failed_count','errors_count','missing_machine','explicit_result_failure']:
                data=json.loads((out/'devtool-invoke.json').read_text())
                if variant=='failed_status':data['machine']['operation']['status']='failed'
                if variant=='failed_count':data['totals']['failed']=1
                if variant=='errors_count':data['totals']['errors']=1
                if variant=='missing_machine':del data['machine']
                if variant=='explicit_result_failure':data['result']={'success':False}
                (out/'devtool-invoke.json').write_text(json.dumps(data))
                import hashlib
                digest=hashlib.sha256((out/'devtool-invoke.json').read_bytes()).hexdigest()
                sums=(out/'SHA256SUMS').read_text().splitlines()
                (out/'SHA256SUMS').write_text('\n'.join(
                    digest+'  devtool-invoke.json' if line.endswith('  devtool-invoke.json') else line
                    for line in sums)+'\n')
                with self.subTest(variant=variant):
                    with self.assertRaises(a05.ProofError):
                        a05.verify_local(out,run_id=RUN,attempt=1,source_sha=SHA)
                # Reset without weakening signed evidence fixture.
                machine_outputs(inp)
                a05.record(out,SHA,a05.DEVTOOL_SHA,a05.REPO,RUN,1,inp)

if __name__=='__main__':unittest.main()
