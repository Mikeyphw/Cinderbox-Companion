"""Host-only contracts for manual, signed, non-publishing GitHub release candidate."""
from __future__ import annotations
import base64
import hashlib
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import m21_actions_release as m
ROOT=HERE.parents[1]
RELEASE='a'*64
DEBUG='b'*64
SHA='d93d21d2f569d947bce91099ef112e3b6a793452'

class ManualCandidateTests(unittest.TestCase):
    def test_separate_release_signer_required(self):
        with patch.dict(os.environ, {'CINDERBOX_RELEASE_CERT_SHA256':RELEASE,
                                     'CINDERBOX_DEBUG_CERT_SHA256':RELEASE}):
            with self.assertRaisesRegex(m.GateError,'M21_RELEASE_MUST_NOT_REUSE_DEBUG_CERT'):
                m.compare_pins()

    def test_no_signing_secrets_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{
            'CINDERBOX_RELEASE_CERT_SHA256':RELEASE,
            'CINDERBOX_DEBUG_CERT_SHA256':DEBUG,
            'CINDERBOX_RELEASE_KEYSTORE_B64':'',
            'STORE_PASSWORD':'','KEY_PASSWORD':''}):
            with self.assertRaisesRegex(m.GateError,'M21_RELEASE_SECRETS_MISSING'):
                m.provision(Path(temp)/'source',Path(temp))

    def test_keystore_certificate_must_match_independent_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);(t/'source').mkdir()
            with patch.dict(os.environ,{'CINDERBOX_RELEASE_CERT_SHA256':RELEASE,
                'CINDERBOX_DEBUG_CERT_SHA256':DEBUG,
                'CINDERBOX_RELEASE_KEYSTORE_B64':base64.b64encode(b'q'*2048).decode(),
                'STORE_PASSWORD':'not-a-real-password','KEY_PASSWORD':'not-a-real-password'}),\
                 patch.object(m,'run',return_value=b'not-the-release-certificate'):
                with self.assertRaisesRegex(m.GateError,'M21_RELEASE_KEYSTORE_CERTIFICATE_MISMATCH'):
                    m.provision(t/'source',t)
                self.assertFalse((t/'source'/'keystore.jks').exists())

    def test_signed_apk_is_verified_before_candidate_output(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);dir=t/'app/build/outputs/apk/release';dir.mkdir(parents=True)
            (dir/'candidate.apk').write_bytes(b'signed synthetic bytes')
            badges="package: name='com.sdvsync' versionCode='14' versionName='0.1.1'\n"
            signature=f'Signer #1 certificate SHA-256 digest: {RELEASE}\n'
            with patch.dict(os.environ,{'CINDERBOX_RELEASE_CERT_SHA256':RELEASE,
                                        'CINDERBOX_DEBUG_CERT_SHA256':DEBUG}),\
                 patch.object(m,'run',side_effect=[signature,badges]),\
                 patch.object(m,'android_build_tool',side_effect=lambda name:name):
                m.verify(t,t/'out',SHA,'38946596038')
            a=t/'out'/'CinderboxCompanion-release-candidate.apk'
            self.assertEqual(a.read_bytes(),b'signed synthetic bytes')
            import json
            e=json.loads((t/'out'/'M21_RELEASE_CANDIDATE.json').read_text())
            self.assertEqual(e['source_commit'],SHA)
            self.assertFalse(e['publication_allowed'])
            self.assertFalse(e['release_qualified'])
            self.assertFalse(e['installed'])

    def test_debuggable_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);dir=t/'app/build/outputs/apk/release';dir.mkdir(parents=True)
            (dir/'candidate.apk').write_bytes(b'synthetic')
            badges="package: name='com.sdvsync' versionCode='14' versionName='0.1.1'\napplication-debuggable\n"
            signature=f'Signer #1 certificate SHA-256 digest: {RELEASE}\n'
            with patch.dict(os.environ,{'CINDERBOX_RELEASE_CERT_SHA256':RELEASE,
                                        'CINDERBOX_DEBUG_CERT_SHA256':DEBUG}),\
                 patch.object(m,'run',side_effect=[signature,badges]),\
                 patch.object(m,'android_build_tool',side_effect=lambda name:name):
                with self.assertRaisesRegex(m.GateError,'M21_RELEASE_APK_DEBUGGABLE'):
                    m.verify(t,t/'out',SHA,'38946596038')
            self.assertFalse((t/'out').exists())

    def test_android_build_tool_uses_pinned_sdk_not_runner_path(self):
        with tempfile.TemporaryDirectory() as temp:
            sdk=Path(temp)
            bt=sdk/'build-tools'/'35.0.0'
            bt.mkdir(parents=True)
            for tool in ('apksigner','aapt'):
                binary=bt/tool
                binary.write_text('tool')
                binary.chmod(0o700)
            with patch.dict(os.environ,{'ANDROID_HOME':str(sdk)},clear=False),\
                 patch.object(m.shutil,'which',return_value='/other/sdk/tool'):
                self.assertEqual(m.android_build_tool('apksigner'),str(bt/'apksigner'))
                self.assertEqual(m.android_build_tool('aapt'),str(bt/'aapt'))

    def test_missing_pinned_apksigner_is_explicit_not_false_signature_failure(self):
        with tempfile.TemporaryDirectory() as temp,\
             patch.dict(os.environ,{'ANDROID_HOME':str(Path(temp))},clear=False):
            with self.assertRaisesRegex(m.GateError,'M21_APKSIGNER_PINNED_SDK_TOOL_UNAVAILABLE'):
                m.android_build_tool('apksigner')

    def test_no_unapproved_tool_selection(self):
        with self.assertRaisesRegex(m.GateError,'M21_BUILD_TOOL_NOT_ALLOWLISTED'):
            m.android_build_tool('zipalign')

    def test_manual_workflow_never_runs_from_pr_or_publishes(self):
        wf=(ROOT/'.github/workflows/cinderbox-release-candidate.yml').read_text()
        self.assertIn('workflow_dispatch:',wf)
        self.assertNotIn('pull_request:',wf)
        self.assertNotIn('push:',wf)
        self.assertIn("github.ref == 'refs/heads/master'",wf)
        self.assertIn('environment: cinderbox-release',wf)
        self.assertIn(SHA,wf)
        self.assertIn('ref: ${{ inputs.reviewed_source_sha }}',wf)
        self.assertIn('persist-credentials: false',wf)
        self.assertIn(':app:assembleRelease',wf)
        self.assertNotIn('gh release create',wf)
        self.assertNotIn('softprops/action-gh-release',wf)
        self.assertNotIn('actions/create-release',wf)
        self.assertIn('source/keystore.jks',wf)
        self.assertIn('Remove temporary signing keystore before artifact upload',wf)
        self.assertIn('M21_RELEASE_CANDIDATE.json',wf)
        self.assertNotIn('${{ secrets.CINDERBOX_DEBUG_KEYSTORE_B64 }}',wf)

if __name__=='__main__':unittest.main()
