"""M16 fail-closed signing tests; no device/network/release access."""
from pathlib import Path
import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m16_debug_signing as m16

ROOT = Path(__file__).resolve().parents[2]


class DebugSigningTests(unittest.TestCase):
    def test_source_contract(self):
        m16.source_contract(ROOT)

    def test_different_certificate_pin_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {m16.PIN: '0'*64}):
                with self.assertRaisesRegex(m16.GateError, 'EXPECTED_EXACTLY_ONE_APK'):
                    m16.verify([Path(temp)])

    def test_missing_pin_does_not_accept_apk(self):
        with patch.dict(os.environ, {m16.PIN: ''}):
            with self.assertRaisesRegex(m16.GateError, 'INVALID_CERTIFICATE_PIN'):
                m16.verify([Path('/not-real')])

    def test_wrong_repository(self):
        env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY='someone/else', GITHUB_EVENT_NAME='push')
        with self.assertRaisesRegex(m16.GateError, 'CI_REPOSITORY_NOT_AUTHORIZED'):
            m16.check_event(env)

    def test_wrong_ci_event(self):
        env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=m16.REPO, GITHUB_EVENT_NAME='issues')
        with self.assertRaisesRegex(m16.GateError, 'CI_EVENT_NOT_AUTHORIZED'):
            m16.check_event(env)

    def test_forked_pull_request_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'event.json'
            path.write_text(json.dumps({'pull_request': {'head': {'repo': {'full_name': 'bad/fork'}},
                                                          'base': {'repo': {'full_name': m16.REPO}}}}))
            env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=m16.REPO,
                       GITHUB_EVENT_NAME='pull_request', GITHUB_EVENT_PATH=str(path))
            with self.assertRaisesRegex(m16.GateError, 'FORK_PR_SIGNING_DENIED'):
                m16.check_event(env)
            event = json.loads(path.read_text())
            event['pull_request']['head']['repo']['full_name'] = m16.REPO
            path.write_text(json.dumps(event))
            m16.check_event(env)

    def test_empty_secrets_fail_before_writing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            keyfile = Path(tmp)/'debug.p12'
            env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=m16.REPO,
                       GITHUB_EVENT_NAME='push')
            with self.assertRaisesRegex(m16.GateError, 'MISSING_DEBUG_SIGNING_CREDENTIALS'):
                m16.provision(keyfile, env)
            self.assertFalse(keyfile.exists())

    def test_symlink_target_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            keyfile = Path(tmp)/'debug.p12'
            keyfile.symlink_to(Path(tmp)/'elsewhere')
            env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=m16.REPO,
                       GITHUB_EVENT_NAME='push', CINDERBOX_DEBUG_KEYSTORE_B64='a',
                       CINDERBOX_DEBUG_STORE_PASSWORD='a'*20,
                       CINDERBOX_DEBUG_KEY_PASSWORD='b'*20,
                       CINDERBOX_DEBUG_CERT_SHA256='0'*64)
            with self.assertRaisesRegex(m16.GateError, 'UNSAFE_KEYSTORE_TARGET'):
                m16.provision(keyfile, env)
            self.assertTrue(keyfile.is_symlink())

    @unittest.skipUnless(__import__('shutil').which('keytool') and __import__('shutil').which('openssl'),
                         'JDK and openssl required for keystore integration regression')
    def test_persistent_keystore_and_bad_pin_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'private'
            m16.setup(directory, upload=False)
            keyfile = directory/'cinderbox-debug.p12'
            password = (directory/'password').read_text()
            digest = m16.fingerprint(keyfile, password)
            self.assertRegex(digest, r'^[a-f0-9]{64}$')
            old_bytes = keyfile.read_bytes()
            m16.setup(directory, upload=False)
            self.assertEqual(old_bytes, keyfile.read_bytes(), 'must reuse original signing identity')
            event = {'pull_request': {'head': {'repo': {'full_name': m16.REPO}},
                                      'base': {'repo': {'full_name': m16.REPO}}}}
            eventpath = Path(tmp)/'event.json'
            eventpath.write_text(json.dumps(event))
            envfile = Path(tmp)/'github-env'
            envfile.touch()
            vals = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=m16.REPO,
                        GITHUB_EVENT_NAME='pull_request', GITHUB_EVENT_PATH=str(eventpath),
                        GITHUB_ENV=str(envfile),
                        CINDERBOX_DEBUG_KEYSTORE_B64=base64.b64encode(old_bytes).decode(),
                        CINDERBOX_DEBUG_STORE_PASSWORD=password,
                        CINDERBOX_DEBUG_KEY_PASSWORD=password,
                        CINDERBOX_DEBUG_CERT_SHA256=digest)
            target = Path(tmp)/'ci-key.p12'
            m16.provision(target, vals)
            self.assertEqual(target.read_bytes(), old_bytes)
            self.assertEqual(target.stat().st_mode & 0o077, 0)
            self.assertIn('CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING=true', envfile.read_text())
            wrong = dict(vals, CINDERBOX_DEBUG_CERT_SHA256='0'*64)
            wrong_path = Path(tmp)/'ci-key-invalid.p12'
            with self.assertRaisesRegex(m16.GateError, 'KEYSTORE_CERTIFICATE_PIN_MISMATCH'):
                m16.provision(wrong_path, wrong)
            self.assertFalse(wrong_path.exists())


if __name__ == '__main__':
    unittest.main()
