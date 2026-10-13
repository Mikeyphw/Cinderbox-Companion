"""Offline M3B fail-closed regression tests; no keystore or Android SDK required."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import m3b_release_candidate as m3b
import m3b_upgrade_preflight as upgrade


class M3BPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / m3b.POLICY).parent.mkdir(parents=True)
        self.doc = {
            'schema_version': 1, 'repository': m3b.REPO, 'package_name': m3b.PACKAGE,
            'keystore_alias': 'cinderbox', 'candidate_signing_enabled': False,
            'certificate_sha256': None, 'publication_enabled': False,
            'automatic_install': False, 'release_qualified': False,
            'device_qualification_complete': False,
        }

    def save(self):
        (self.root / m3b.POLICY).write_text(json.dumps(self.doc))

    def test_disabled_default_passes_read_only_policy(self):
        self.save()
        self.assertFalse(m3b.policy(self.root)['candidate_signing_enabled'])

    def test_disabled_default_rejects_candidate(self):
        self.save()
        with self.assertRaises(m3b.GateError):
            m3b.policy(self.root, require_enabled=True)

    def test_enabled_without_pinned_key_rejected(self):
        self.doc['candidate_signing_enabled'] = True
        self.save()
        with self.assertRaises(m3b.GateError):
            m3b.policy(self.root)

    def test_lowercase_pinned_fingerprint_allows_candidate_policy(self):
        self.doc.update(candidate_signing_enabled=True, certificate_sha256='a'*64)
        self.save()
        self.assertTrue(m3b.policy(self.root, require_enabled=True)['candidate_signing_enabled'])

    def test_publication_can_never_be_enabled(self):
        self.doc['publication_enabled'] = True
        self.save()
        with self.assertRaises(m3b.GateError):
            m3b.policy(self.root)

    def test_automatic_install_can_never_be_enabled(self):
        self.doc['automatic_install'] = True
        self.save()
        with self.assertRaises(m3b.GateError):
            m3b.policy(self.root)

    def test_unrecognized_policy_field_is_refused(self):
        self.doc['skip_signing'] = True
        self.save()
        with self.assertRaises(m3b.GateError):
            m3b.policy(self.root)

    def test_rejects_unknown_or_malformed_apk(self):
        candidate = self.root / 'bad.apk'
        candidate.write_bytes(b'A'*6000)
        with self.assertRaises(m3b.GateError):
            m3b.inspect_apk(candidate)

    def test_extra_zip_members_or_duplicate_denied(self):
        candidate = self.root / 'dup.apk'
        with zipfile.ZipFile(candidate, 'w') as z:
            z.writestr('AndroidManifest.xml', 'a'*4096)
            z.writestr('classes.dex', 'dex')
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr('classes.dex', 'dex')
        with self.assertRaises(m3b.GateError):
            m3b.inspect_apk(candidate)

    def test_certificate_mismatch_rejected(self):
        self.doc.update(candidate_signing_enabled=True, certificate_sha256='a'*64)
        self.save()
        candidate = self.root / 'candidate.apk'
        candidate.write_bytes(b'fixture')
        actual = {'package_name': m3b.PACKAGE, 'version_code': 14,
                  'certificate_sha256': 'b'*64, 'sha256': 'c'*64}
        with patch.object(m3b, '_run', return_value='f'*40), \
             patch.object(m3b, 'inspect_apk', return_value=actual):
            with self.assertRaisesRegex(m3b.GateError, 'pinned stable signing key'):
                m3b.generate(self.root, candidate, self.root/'out.json', 'f'*40, '1234')
        self.assertFalse((self.root/'out.json').exists())


class CertificateOutputCompatibilityTests(unittest.TestCase):
    def test_m3_debug_reordered_dn_and_colon_fingerprint(self):
        import m3_build_evidence as debug
        digest = 'ab'*32
        separated = ':'.join(['ab']*32)
        certs = ('Signer #1 certificate DN: C=US, O=Android, CN=Android Debug\n'
                 'Signer #1 certificate SHA-256 digest:\n' + separated + '\n')
        badging = "package: name='com.sdvsync' versionCode='14' versionName='0.1.1'"
        with patch.object(debug, 'certificate_sha256', return_value=digest), \
             patch.object(debug, 'is_android_debug_certificate', return_value=True), \
             patch.object(debug, '_tool', side_effect=lambda name: name), \
             patch.object(debug, '_run', side_effect=[certs, badging]):
            self.assertEqual(debug.inspect_android(Path('fixture.apk'))['signing_certificate_sha256'], digest)

    def test_m3_debug_rejects_second_signer(self):
        import m3_build_evidence as debug
        certs = ('Signer #1 certificate DN: CN=Android Debug, O=Android\n'
                 'Signer #1 certificate SHA-256 digest: ' + 'ab'*32 + '\n'
                 'Signer #2 certificate SHA-256 digest: ' + 'cd'*32 + '\n')
        with patch.object(debug, 'certificate_sha256', side_effect=debug.SigningBlockError('APK signing schemes disagree')), \
             patch.object(debug, '_tool', return_value='apksigner'), \
             patch.object(debug, '_run', return_value=certs):
            with self.assertRaises(debug.SigningBlockError):
                debug.inspect_android(Path('fixture.apk'))

    def test_release_candidate_parses_linewrapped_hex_fingerprint(self):
        from m3b_release_candidate import inspect_apk
        with tempfile.TemporaryDirectory() as td:
            candidate = Path(td) / 'signed.apk'
            with zipfile.ZipFile(candidate, 'w') as z:
                z.writestr('AndroidManifest.xml', 'x'*4096)
                z.writestr('classes.dex', 'dex'*900)
            certs = 'Signer #1 certificate SHA-256 digest:\n' + 'cd'*32 + '\n'
            badging = "package: name='com.sdvsync' versionCode='14' versionName='0.1.1'"
            with patch.object(m3b, 'certificate_sha256', return_value='cd'*32), \
                 patch.object(m3b, '_tool', side_effect=lambda name: name), \
                 patch.object(m3b, '_run', side_effect=[certs, badging]):
                self.assertEqual(inspect_apk(candidate)['certificate_sha256'], 'cd'*32)


class M3BDeviceTest(unittest.TestCase):
    def test_rejects_invalid_device_serial(self):
        with self.assertRaises(m3b.GateError):
            upgrade.preflight('bad serial; rm -rf /', Path('candidate.apk'))

    def test_rejects_unauthorized_device(self):
        fake = type('Proc', (), {'returncode': 0, 'stdout': 'List of devices attached\nfoo\toffline\n'})()
        with patch.object(upgrade.subprocess, 'run', return_value=fake):
            with self.assertRaises(m3b.GateError):
                upgrade.preflight('foo', Path('candidate.apk'))

    def test_upgrade_signing_mismatch_blocked(self):
        # Simulated authorized ADB responses; no actual ADB or changes to device.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            responses = ['34', 'package:/data/app/abc/base.apk', '']
            def apk_info(path):
                cert = 'a'*64 if path.name == 'candidate.apk' else 'b'*64
                return {'certificate_sha256': cert, 'version_code': 14}
            fake = type('Proc', (), {'returncode': 0, 'stdout': 'List of devices attached\nfoo\tdevice\n'})()
            with patch.object(upgrade.subprocess, 'run', return_value=fake), \
                 patch.object(upgrade, 'adb', side_effect=responses), \
                 patch.object(upgrade, 'inspect_apk', side_effect=apk_info):
                with self.assertRaisesRegex(m3b.GateError, 'Signing mismatch'):
                    upgrade.preflight('foo', Path(td)/'candidate.apk')

    def test_new_install_is_not_reported_as_upgrade(self):
        fake = type('Proc', (), {'returncode': 0, 'stdout': 'List of devices attached\nfoo\tdevice\n'})()
        with patch.object(upgrade.subprocess, 'run', return_value=fake), \
             patch.object(upgrade, 'adb', side_effect=['34', '']), \
             patch.object(upgrade, 'inspect_apk', return_value={'certificate_sha256': 'a'*64, 'version_code': 14}):
            self.assertIn('NEW INSTALL ONLY', upgrade.preflight('foo', Path('candidate.apk')))


if __name__ == '__main__':
    unittest.main()
