"""M13 qualification evidence must fail closed even when existing CI is green."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/devtool/m13_qualification.py'
spec = importlib.util.spec_from_file_location('m13_qualification', SCRIPT)
qual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qual)


def run(sha='a' * 40):
    return dict(id=12345678, name='Build Debug APK', status='completed',
                conclusion='success', event='pull_request', head_sha=sha,
                repository={'full_name':qual.REPO})


def jobs():
    return {'jobs':[{'name':'build','conclusion':'success',
       'steps':[{'name':n,'conclusion':'success'} for n in qual.REQUIRED_CI_STEPS]}]}


class M13QualificationTests(unittest.TestCase):
    def test_completed_ci_has_debug_only_status(self):
        result = qual.assess_ci(run(), jobs(), 'a'*40)
        self.assertEqual('PASS_GITHUB_REST_OBSERVATION', result['ci_run'])
        self.assertFalse(result['release_qualified'])
        self.assertFalse(result['publication_allowed'])
        self.assertEqual('NOT_RUN', result['instrumentation'])

    def test_pending_ci_is_not_success(self):
        fixture=run(); fixture['status']='in_progress'; fixture['conclusion']=None
        with self.assertRaises(qual.GateError):qual.assess_ci(fixture,jobs(),'a'*40)

    def test_different_commit_is_not_success(self):
        with self.assertRaises(qual.GateError):qual.assess_ci(run(),jobs(),'b'*40)

    def test_skipped_lint_test_or_evidence_blocks(self):
        for required in qual.REQUIRED_CI_STEPS:
            fixture=jobs()
            for step in fixture['jobs'][0]['steps']:
                if step['name']==required: step['conclusion']='skipped'
            with self.subTest(required=required),self.assertRaises(qual.GateError):
                qual.assess_ci(run(),fixture,'a'*40)

    def test_duplicate_step_names_refused(self):
        fixture=jobs()
        fixture['jobs'][0]['steps'].append(fixture['jobs'][0]['steps'][0])
        with self.assertRaises(qual.GateError):qual.assess_ci(run(),fixture,'a'*40)

    def test_false_local_artifact_or_release_claim_refused(self):
        base={'producer':'cinderbox-m13','source_commit':'a'*40,'source_contract':'PASS',
              'apk_integrity':'PASS_SHA256_MATCHES_M3','artifact_sha256':'d'*64,
              'release_qualified':False}
        good=qual.assess_ci(run(),jobs(),'a'*40,base)
        self.assertEqual('d'*64,good['artifact_sha256'])
        for corruption in ({'release_qualified':True},{'source_commit':'b'*40},
                           {'apk_integrity':'NOT_RUN'}):
            item=base|corruption
            with self.assertRaises(qual.GateError):qual.assess_ci(run(),jobs(),'a'*40,item)

    def test_m3_bound_apk_rejects_tamper_and_false_release_status(self):
        actual_commit=qual.current_commit(ROOT)
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); apk=base/'debug.apk'; apk.write_bytes(b'forged-test-fixture')
            data={'schema_version':1,'evidence_kind':'ci-build-self-report',
                  'source_commit':actual_commit,'repository':qual.REPO,
                  'variant':'debug','format':'apk',
                  'qualified_release':False,'publication_allowed':False,
                  'reproducibility_proven':False,'device_qualified':False,
                  'apk':{'filename':apk.name,'size_bytes':apk.stat().st_size,
                         'sha256':qual.sha256(apk), 'signature_verified':True,
                         'debug_signed':True,'package_name':'com.sdvsync'}}
            provenance=base/'M3_PROVENANCE.json'
            provenance.write_text(json.dumps(data))
            result=qual.finalize(ROOT,provenance,apk,actual_commit)
            self.assertEqual('PASS_SHA256_MATCHES_M3',result['apk_integrity'])
            self.assertFalse(result['release_qualified'])
            apk.write_bytes(b'changed')
            with self.assertRaises(qual.GateError):
                qual.finalize(ROOT,provenance,apk,actual_commit)
            apk.write_bytes(b'forged-test-fixture')
            data['qualified_release']=True
            provenance.write_text(json.dumps(data))
            with self.assertRaises(qual.GateError):
                qual.finalize(ROOT,provenance,apk,actual_commit)

    def test_bad_json_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.json'; p.write_text('{bad json')
            with self.assertRaises(qual.GateError):qual.load_json(p)
            p.write_text('{}')
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(qual.GateError):qual.load_json(link)

    def test_preflight_source_links_required_milestones(self):
        # This must run on the real checkout, not a fabricated source tree.
        inspected=qual.source_audit(ROOT)
        self.assertEqual('PASS',inspected['debug_source_contract'])
        self.assertEqual(5,len(inspected['cross_feature_checks']))
        self.assertEqual('BLOCKED_BY_POLICY',inspected['release_policy'])

    def test_signed_candidate_is_not_mistaken_for_release(self):
        candidate=qual.load_json(ROOT/'docs/security/M3B_CANDIDATE_POLICY.json')
        self.assertFalse(candidate['publication_enabled'])
        self.assertFalse(candidate['release_qualified'])
        self.assertFalse(candidate['automatic_install'])
        self.assertFalse(candidate['device_qualification_complete'])

    def test_ci_workflow_outputs_are_not_releasable(self):
        for wf in qual.WORKFLOWS:
            data=(ROOT/wf).read_text()
            self.assertIn('m13_qualification.py source',data)
            self.assertIn('m13_qualification.py finalize',data)
            self.assertIn('M13_QUALIFICATION.json',data)
            self.assertNotIn('assembleRelease',data)

if __name__=='__main__':unittest.main()
