"""A05 source-bound CI/EXO gate regressions: no remote calls or device mutation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/devtool'))
import a05_actions_qualification as a05

class A05QualificationTests(unittest.TestCase):
    def test_source_contract_existing_target_workflow_and_wrapper(self):
        self.assertEqual(a05.source()['overall'],'PASS_CINDERBOX_A05_SOURCE_CONTRACT')
    def test_registered_existing_workflow_not_replaced(self):
        flow=(ROOT/a05.WORKFLOW).read_text()
        self.assertIn('name: Devtool Android Build',flow)
        self.assertIn('build-debug-apk:',flow)
        self.assertIn('uses: ./.github/workflows/build.yml',flow)
        self.assertIn('name: debug-apk',(ROOT/'.github/workflows/build.yml').read_text())
        self.assertIn('a05-native-devtool-dag:',flow)
        self.assertEqual(flow.count('workflow_dispatch:'),1)
        self.assertIn('persist-credentials: false',flow)
        self.assertIn("default: 'native-only'",flow)
        self.assertIn("if: ${{ inputs.a05_mode != 'native-only' }}",flow)
        self.assertIn("if: ${{ inputs.a05_mode == 'native-only' || inputs.a05_mode == 'both' }}",flow)
    def test_source_and_devtool_sha_pin(self):
        flow=(ROOT/a05.WORKFLOW).read_text()
        self.assertIn(a05.DEVTOOL_SHA,flow)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',flow)
        self.assertIn('git -C "$RUNNER_TEMP/devtool-a05" rev-parse HEAD',flow)
        self.assertIn('actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09',flow)
        self.assertIn('actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4',flow)
    def test_unittest_yaml_parses_its_exact_job(self):
        flow=(ROOT/a05.WORKFLOW).read_text()
        # Works with stdlib only (Termux does not require optional PyYAML).
        self.assertEqual(flow.count('  a05-native-devtool-dag:'),1)
        self.assertEqual(flow.count('  build-debug-apk:'),1)
        lane=flow.split('  a05-native-devtool-dag:',1)[1]
        self.assertIn('    permissions:\n      contents: read',lane)
        self.assertEqual(lane.count('        uses:'),2)
    def test_no_new_mutating_behavior(self):
        flow=(ROOT/a05.WORKFLOW).read_text().split('  a05-native-devtool-dag:')[1]
        for forbidden in ('adb install','assembleRelease','sudo ','gh release create','contents: write','id-token: write','secrets.'):
            self.assertNotIn(forbidden,flow)
    def _fixture(self):
        t=tempfile.TemporaryDirectory()
        root=Path(t.name);inputs=root/'input';out=root/'evidence';inputs.mkdir()
        for name in a05.FILES[3:]:
            (inputs/name).write_text(json.dumps({'ok':True,'exit_code':0,'result':{'success':True}}))
        sha='b'*40
        a05.record(out,sha,a05.DEVTOOL_SHA,a05.REPO,87654,1,inputs)
        return t, out, sha
    def test_local_evidence_positive(self):
        t,out,sha=self._fixture()
        try:self.assertEqual(a05.verify_local(out,run_id=87654,attempt=1,source_sha=sha)['overall'],'PASS_CINDERBOX_A05_LOCAL_EVIDENCE_VERIFIED')
        finally:t.cleanup()
    def test_checksum_tamper_rejected(self):
        t,out,sha=self._fixture()
        try:
            (out/'devtool-invoke.json').write_text('{"ok": false}')
            with self.assertRaisesRegex(a05.ProofError,'checksum'):a05.verify_local(out,run_id=87654,attempt=1,source_sha=sha)
        finally:t.cleanup()
    def test_attempt_reuse_rejected(self):
        t,out,sha=self._fixture()
        try:
            with self.assertRaisesRegex(a05.ProofError,'exact run'):a05.verify_local(out,run_id=87654,attempt=2,source_sha=sha)
        finally:t.cleanup()
    def test_wrong_source_rejected(self):
        t,out,sha=self._fixture()
        try:
            with self.assertRaisesRegex(a05.ProofError,'exact run'):a05.verify_local(out,run_id=87654,attempt=1,source_sha='a'*40)
        finally:t.cleanup()
    def test_false_machine_success_rejected_even_if_checksums_valid(self):
        t,out,sha=self._fixture()
        try:
            p=out/'devtool-invoke.json';p.write_text('{"ok":false,"exit_code":1,"result":{"success":false}}')
            lines=(out/'SHA256SUMS').read_text().splitlines()
            (out/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  devtool-invoke.json' if x.endswith('  devtool-invoke.json') else x for x in lines)+'\n')
            with self.assertRaisesRegex(a05.ProofError,'did not pass'):a05.verify_local(out,run_id=87654,attempt=1,source_sha=sha)
        finally:t.cleanup()
    def test_incomplete_machine_evidence_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inp=root/'in';inp.mkdir()
            meta=a05.record(root/'out','c'*40,a05.DEVTOOL_SHA,a05.REPO,1,1,inp)
            self.assertFalse(meta['complete'])
            with self.assertRaises(a05.ProofError):a05.verify_local(root/'out',run_id=1,attempt=1,source_sha='c'*40)
    def test_unknown_extra_evidence_is_rejected(self):
        t,out,sha=self._fixture()
        try:
            (out/'untracked').write_text('unexpected')
            with self.assertRaisesRegex(a05.ProofError,'additional'):
                a05.verify_local(out,run_id=87654,attempt=1,source_sha=sha)
        finally:t.cleanup()
    def test_report_false_release_qualification_rejected(self):
        t,out,sha=self._fixture()
        try:
            p=out/'RUN_META.json';j=json.loads(p.read_text());j['release_qualified']=True;p.write_text(json.dumps(j))
            lines=(out/'SHA256SUMS').read_text().splitlines()
            (out/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  RUN_META.json' if x.endswith('  RUN_META.json') else x for x in lines)+'\n')
            with self.assertRaisesRegex(a05.ProofError,'false release'):
                a05.verify_local(out,run_id=87654,attempt=1,source_sha=sha)
        finally:t.cleanup()
    def test_wrong_dispatch_mode_is_rejected_without_download(self):
        sha='a'*40
        run={'id':555,'head_sha':sha,'event':'workflow_dispatch','status':'completed',
             'path':a05.WORKFLOW+'@refs/heads/feature','run_attempt':1,
             'conclusion':'success','inputs':{'a05_mode':'off'}}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',return_value=run):
                with self.assertRaisesRegex(a05.ProofError,'mode'):
                    a05.verify_run(555,Path(d)/'evidence',sha,'native-only')
    def test_gh_mismatched_run_rejected_pre_download(self):
        fake={'id':123,'head_sha':'f'*40,'event':'workflow_dispatch','status':'completed', 'path':a05.WORKFLOW+'@refs/heads/master'}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',return_value=fake) as api:
                with patch.object(a05.subprocess,'run') as sub:
                    with self.assertRaisesRegex(a05.ProofError,'mismatched'):a05.verify_run(123,Path(d)/'evidence','e'*40,'native-only')
                    sub.assert_not_called()
    def test_successful_exact_remote_evidence_verification(self):
        sha='a'*40
        run={'id':777,'head_sha':sha,'event':'workflow_dispatch','status':'completed',
             'path':a05.WORKFLOW+'@refs/heads/feature','run_attempt':2,
             'conclusion':'success','inputs':{'a05_mode':'native-only'}}
        jobs={'total_count':2,'jobs':[{'name':'A05 native DAG + EXO evidence',
                                      'conclusion':'success','run_attempt':2},
                                     {'name':'build-debug-apk','conclusion':'skipped','run_attempt':2}]}
        artifacts={'total_count':1,'artifacts':[{'name':a05.ARTIFACT,'id':42,'expired':False,
                                                'workflow_run':{'id':777}}]}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'download';target.mkdir()
            tmp, fixture, _ = self._fixture()
            try:
                # Build exact-attempt evidence rather than just reusing its checksum.
                inp=root/'inputs';inp.mkdir()
                for name in a05.FILES[3:]:
                    (inp/name).write_text(json.dumps({'ok':True,'exit_code':0,'result':{'success':True}}))
                a05.record(fixture,sha,a05.DEVTOOL_SHA,a05.REPO,777,2,inp)
                with patch.object(a05,'_gh_api',side_effect=[run,jobs,artifacts]):
                    def download(cmd,**kwargs):
                        self.assertIn('--name',cmd)
                        for f in fixture.iterdir():
                            (target/f.name).write_bytes(f.read_bytes())
                        return subprocess.CompletedProcess(cmd,0,'','')
                    with patch.object(a05.subprocess,'run',side_effect=download):
                        result=a05.verify_run(777,target,sha,'native-only')
                self.assertEqual(result['overall'],'PASS_CINDERBOX_A05_GITHUB_RUN_VERIFIED')
                self.assertEqual(result['attempt'],2)
                self.assertEqual(result['artifact_id'],42)
                self.assertFalse(result['release_qualified'])
            finally:tmp.cleanup()
    def test_both_mode_requires_successful_build_job(self):
        sha='a'*40
        run={'id':555,'head_sha':sha,'event':'workflow_dispatch','status':'completed',
             'path':a05.WORKFLOW+'@refs/heads/feature','run_attempt':1,
             'conclusion':'success','inputs':{'a05_mode':'both'}}
        jobs={'total_count':2,'jobs':[{'name':'A05 native DAG + EXO evidence','conclusion':'success'},
                                      {'name':'build-debug-apk','conclusion':'skipped'}]}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',side_effect=[run,jobs]):
                with self.assertRaisesRegex(a05.ProofError,'Android build'):
                    a05.verify_run(555,Path(d)/'evidence',sha,'both')
    def test_remote_job_failure_rejected(self):
        sha='a'*40
        run={'id':555,'head_sha':sha,'event':'workflow_dispatch','status':'completed',
             'path':a05.WORKFLOW+'@refs/heads/feature','run_attempt':1,'conclusion':'failure','inputs':{'a05_mode':'native-only'}}
        jobs={'total_count':1,'jobs':[{'name':'A05 native DAG + EXO evidence','conclusion':'failure'}]}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',side_effect=[run,jobs]):
                with self.assertRaisesRegex(a05.ProofError,'not successful'):a05.verify_run(555,Path(d)/'evidence',sha,'native-only')
    def test_remote_full_failed_run_cannot_qualify(self):
        sha='a'*40
        run={'id':555,'head_sha':sha,'event':'workflow_dispatch','status':'completed',
             'path':a05.WORKFLOW+'@refs/heads/feature','run_attempt':1,'conclusion':'failure','inputs':{'a05_mode':'native-only'}}
        jobs={'total_count':1,'jobs':[{'name':'A05 native DAG + EXO evidence','conclusion':'success'}]}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(a05,'_gh_api',side_effect=[run,jobs]):
                with self.assertRaisesRegex(a05.ProofError,'GitHub workflow'):a05.verify_run(555,Path(d)/'evidence',sha,'native-only')

if __name__=='__main__':unittest.main()
