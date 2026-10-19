"""A07 host evidence checks; no device, signing credential or GitHub request."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import a07_native_debug as a

SHA='a'*40

def jwrite(path, value):
    path.write_text(json.dumps(value,sort_keys=True)+'\n')

class A07ContractTests(unittest.TestCase):
    def test_source_contract(self):
        a.source_contract()

    def fixture(self,root):
        machine=root/'machine';proof=root/'apk';machine.mkdir();proof.mkdir()
        for name in a.MACHINE:
            d={'ok':True,'exit_code':0,'machine':{'operation':{'status':'ok','detail':''}}}
            if name=='a07-invoke.json':
                d['machine']['operation']['detail']='\n'.join(
                    'job:cinderbox.'+x+': ok exit=0' for x in
                    ('security-contract','debug-apk','verify-debug-apk'))
            jwrite(machine/name,d)
        (proof/'debug.apk').write_bytes(b'APK\0'*2048)
        want=a.digest(proof/'debug.apk')
        (proof/'SHA256SUMS').write_text(f'{want}  debug.apk\n')
        jwrite(proof/'M3_PROVENANCE.json',{
            'repository':a.REPO,'source_commit':SHA,'variant':'debug','format':'apk',
            'evidence_kind':'ci-build-self-report','qualified_release':False,
            'publication_allowed':False,'reproducibility_proven':False,
            'device_qualified':False,
            'apk':{'filename':'debug.apk','size_bytes':8192,'sha256':want,
                   'package_name':'com.sdvsync','signature_verified':True,
                   'debug_signed':True,'signing_certificate_sha256':'b'*64}})
        jwrite(proof/'M13_QUALIFICATION.json',{'producer':'cinderbox-m13',
              'source_commit':SHA,'artifact_sha256':want,
              'apk_integrity':'PASS_SHA256_MATCHES_M3','release_qualified':False,
              'device_qualified':False})
        return machine,proof

    def record_ok(self,machine,proof):
        with patch.dict('os.environ',{'GITHUB_SHA':SHA,'GITHUB_REPOSITORY':a.REPO,
                 'GITHUB_RUN_ID':'99','GITHUB_RUN_ATTEMPT':'1'}):
            return a.record(machine,machine,proof,False)

    def test_good_local_consistency_does_not_qualify_github(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t))
            result=self.record_ok(m,p)
            self.assertTrue(result['complete'])
            verdict=a.verify_local(m,p,SHA,99,1)
            self.assertEqual(verdict['overall'],'PASS_CINDERBOX_A07_LOCAL_ARTIFACT_CONSISTENCY')
            self.assertFalse(verdict['github_run_qualified'])
            self.assertFalse(verdict['android_device_qualified'])
            self.assertFalse(verdict['release_qualified'])

    def test_apk_tampering_denied(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t));self.record_ok(m,p)
            with (p/'debug.apk').open('ab') as f:f.write(b'WRONG')
            with self.assertRaises(a.Refused):a.verify_local(m,p,SHA,99,1)

    def test_missing_native_node_denied(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t))
            d=a.read_json(m/'a07-invoke.json')
            d['machine']['operation']['detail']='job:cinderbox.security-contract: ok'
            jwrite(m/'a07-invoke.json',d)
            with self.assertRaises(a.Refused):self.record_ok(m,p)

    def test_unqualified_machine_denied(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t));self.record_ok(m,p)
            d=a.read_json(m/'a07-preflight.json');d['ok']=False
            jwrite(m/'a07-preflight.json',d)
            with self.assertRaises(a.Refused):a.verify_local(m,p,SHA,99,1)

    def test_wrong_run_or_source_denied(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t));self.record_ok(m,p)
            for sha,run,attempt in [(SHA,100,1),(SHA,99,2),('b'*40,99,1)]:
                with self.subTest(sha=sha,run=run,attempt=attempt):
                    with self.assertRaises(a.Refused):a.verify_local(m,p,sha,run,attempt)

    def test_wrong_signer_or_m13_claim_denied(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t))
            d=a.read_json(p/'M3_PROVENANCE.json')
            d['apk']['signing_certificate_sha256']='invalid'
            jwrite(p/'M3_PROVENANCE.json',d)
            with self.assertRaises(a.Refused):self.record_ok(m,p)
            d['apk']['signing_certificate_sha256']='b'*64
            jwrite(p/'M3_PROVENANCE.json',d)
            d=a.read_json(p/'M13_QUALIFICATION.json')
            d['release_qualified']=True
            jwrite(p/'M13_QUALIFICATION.json',d)
            with self.assertRaises(a.Refused):self.record_ok(m,p)

    def test_fail_record_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as t:
            m,p=self.fixture(Path(t))
            with patch.dict('os.environ',{'GITHUB_SHA':SHA,'GITHUB_REPOSITORY':a.REPO,
                    'GITHUB_RUN_ID':'99','GITHUB_RUN_ATTEMPT':'1'}):
                doc=a.record(m,m,None,True)
            self.assertFalse(doc['complete'])
            with self.assertRaises(a.Refused):a.verify_local(m,p,SHA,99,1)

    def test_github_run_never_accepted_from_self_report_alone(self):
        with patch.object(a,'_gh_json',side_effect=a.Refused('remote unavailable')):
            with self.assertRaises(a.Refused):a.verify_run(99,1,SHA)

if __name__=='__main__':unittest.main()
