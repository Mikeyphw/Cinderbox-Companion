"""M21 source-bound regression tests for live GitHub metadata and APK verifier."""
from __future__ import annotations
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import m14_device_qualification as m14
import m21_campaign as m21


class M21IntegrationRegression(unittest.TestCase):
    SOURCE='d93d21d2f569d947bce91099ef112e3b6a793452'
    BASE='feafc8a0fdd3ea2662a168a78e2ba091f0a25d7e'
    CHECKOUT='dc7439617acaa10823a5e9bc95091bf8771f21f2'
    REF='refs/pull/26/merge'

    def fixtures(self, merge_value=None):
        run={'event':'pull_request','head_sha':self.SOURCE,
             'head_branch':'feature/m21-feature-release-readiness',
             'pull_requests':[{'number':26,'head':{'sha':self.SOURCE,'ref':'feature/m21-feature-release-readiness'},
                               'base':{'sha':self.BASE}}]}
        pr={'number':26,'state':'open',
            'head':{'sha':self.SOURCE,'ref':run['head_branch']},
            'base':{'sha':self.BASE},'merge_commit_sha':merge_value}
        ref={'ref':self.REF,'object':{'sha':self.CHECKOUT}}
        commit={'sha':self.CHECKOUT,'parents':[{'sha':self.BASE},{'sha':self.SOURCE}]}
        return run,pr,ref,commit

    def test_recover_null_merge_field_from_verified_immutable_artifact(self):
        run,pr,ref,commit=self.fixtures()
        with patch.object(m14,'json_from_gh',side_effect=[pr,ref,commit]) as api:
            self.assertEqual(m14.verified_ci_checkout(run,self.SOURCE,
                artifact_commit=self.CHECKOUT,artifact_ref=self.REF),
                (self.CHECKOUT,self.REF))
            self.assertEqual(api.call_count,3)

    def test_missing_artifact_is_never_trusted_when_live_merge_sha_null(self):
        run,pr,ref,commit=self.fixtures()
        with patch.object(m14,'json_from_gh',return_value=pr):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_MERGE_COMMIT_UNAVAILABLE'):
                m14.verified_ci_checkout(run,self.SOURCE)

    def test_wrong_immutable_checkout_and_ref_fail_closed(self):
        run,pr,ref,commit=self.fixtures()
        with patch.object(m14,'json_from_gh',side_effect=[pr,ref,commit]):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_MERGE_REF_MISMATCH'):
                m14.verified_ci_checkout(run,self.SOURCE,artifact_commit='c'*40,
                                         artifact_ref=self.REF)
        with patch.object(m14,'json_from_gh',return_value=pr):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_ARTIFACT_REF_MISMATCH'):
                m14.verified_ci_checkout(run,self.SOURCE,artifact_commit=self.CHECKOUT,
                                         artifact_ref='refs/heads/master')

    def test_wrong_parents_fail_closed(self):
        run,pr,ref,commit=self.fixtures()
        commit['parents']=[{'sha':self.SOURCE},{'sha':self.BASE}]
        with patch.object(m14,'json_from_gh',side_effect=[pr,ref,commit]):
            with self.assertRaisesRegex(m14.DeviceGateError,'PR_MERGE_PARENTS_MISMATCH'):
                m14.verified_ci_checkout(run,self.SOURCE,artifact_commit=self.CHECKOUT,
                                         artifact_ref=self.REF)

    def test_binary_signer_independent_of_tool_output(self):
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'test.apk';apk.write_bytes(b'fixture')
            with patch.object(m21.shutil,'which',return_value='/opt/apksigner'),\
                 patch.object(m21,'run_command',return_value='localized output'),\
                 patch.object(m21.signing,'certificate_sha256',return_value='a'*64):
                self.assertEqual(m21.signer_certificate(apk),'a'*64)

    def test_invalid_signature_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'test.apk';apk.write_bytes(b'fixture')
            with patch.object(m21.shutil,'which',return_value='/opt/apksigner'),\
                 patch.object(m21,'run_command',side_effect=m14.DeviceGateError('M21_APK_SIGNATURE_INVALID')):
                with self.assertRaisesRegex(m14.DeviceGateError,'M21_APK_SIGNATURE_INVALID'):
                    m21.signer_certificate(apk)

    def test_multiple_or_conflicting_signers_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'test.apk';apk.write_bytes(b'fixture')
            with patch.object(m21.shutil,'which',return_value='/opt/apksigner'),\
                 patch.object(m21,'run_command',return_value='verified'),\
                 patch.object(m21.signing,'certificate_sha256',side_effect=m21.signing.SigningBlockError('bad')):
                with self.assertRaisesRegex(m14.DeviceGateError,'M21_APK_SIGNING_BLOCK_INVALID'):
                    m21.signer_certificate(apk)

    def test_apk_mutation_during_verification_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'test.apk';apk.write_bytes(b'fixture')
            def mutate(path):
                path.write_bytes(b'mutated')
                return 'a'*64
            with patch.object(m21.shutil,'which',return_value='/opt/apksigner'),\
                 patch.object(m21,'run_command',return_value='verified'),\
                 patch.object(m21.signing,'certificate_sha256',side_effect=mutate):
                with self.assertRaisesRegex(m14.DeviceGateError,'M21_APK_CHANGED_DURING_VERIFICATION'):
                    m21.signer_certificate(apk)


if __name__=='__main__':
    unittest.main()
