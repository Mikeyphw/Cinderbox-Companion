"""Host-only negative tests: source-bound M25 emulator receipt, no Android SDK."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m25_emulator_ci as em
import m25_verify


class EmulatorContractTests(unittest.TestCase):
    @staticmethod
    def response(tests=None, terminal=True, fail=None):
        names = em.TESTS if tests is None else tests
        result = []
        for name in names:
            result += [f'INSTRUMENTATION_STATUS: test={name}',
                       'INSTRUMENTATION_STATUS_CODE: 1',
                       f'INSTRUMENTATION_STATUS: test={name}',
                       'INSTRUMENTATION_STATUS_CODE: ' + ('-2' if name == fail else '0')]
        result.append('OK (4 tests)')
        if terminal:
            result.append('INSTRUMENTATION_CODE: -1')
        return '\n'.join(result)

    def test_valid_four_test_allowlist(self):
        evidence = em.summary(self.response(), 0)
        self.assertTrue(em.good(evidence))
        self.assertEqual(evidence['started_tests'], list(em.TESTS))
        self.assertEqual(evidence['passed_tests'], list(em.TESTS))
        self.assertNotIn('raw_output', evidence)

    def test_refuses_missing_method(self):
        self.assertFalse(em.good(em.summary(self.response(em.TESTS[:-1]), 0)))

    def test_refuses_extra_unexpected_method(self):
        self.assertFalse(em.good(em.summary(self.response((*em.TESTS, 'unknownTest')), 0)))

    def test_refuses_nonterminal_and_failed_test(self):
        self.assertFalse(em.good(em.summary(self.response(terminal=False), 0)))
        self.assertFalse(em.good(em.summary(self.response(fail=em.TESTS[1]), 0)))
        self.assertFalse(em.good(em.summary(self.response(), 1)))

    def test_refuses_repeated_test_status(self):
        payload = self.response()
        first = em.TESTS[0]
        extra = (f'INSTRUMENTATION_STATUS: test={first}\n'
                 'INSTRUMENTATION_STATUS_CODE: 1\n'
                 f'INSTRUMENTATION_STATUS: test={first}\n'
                 'INSTRUMENTATION_STATUS_CODE: 0\n')
        self.assertFalse(em.good(em.summary(extra + payload, 0)))
        self.assertFalse(em.good(em.summary(payload + '\n' + extra, 0)))

    def test_refuses_out_of_order_events(self):
        first = em.TESTS[0]
        swapped = self.response().replace(
            f'INSTRUMENTATION_STATUS: test={first}\nINSTRUMENTATION_STATUS_CODE: 1',
            f'INSTRUMENTATION_STATUS: test={first}\nINSTRUMENTATION_STATUS_CODE: 0', 1)
        self.assertFalse(em.good(em.summary(swapped, 0)))

    def test_refuses_instrumentation_crash(self):
        report = em.summary(self.response() + '\nINSTRUMENTATION_FAILED', 0)
        self.assertFalse(em.good(report))
        self.assertEqual(report['error_categories'], ['instrumentation_crash'])

    def test_scrubs_untrusted_data(self):
        report = em.summary(self.response() + '\n/storage/emulated/0/private.json', 0)
        self.assertTrue(em.good(report))
        self.assertNotIn('/storage/emulated', json.dumps(report))

    def make_identity(self, target: Path):
        identity = dict(schema_version=1, source_sha='a' * 40,
            package='com.sdvsync', app_is_debug=True,
            app_apk_sha256='1' * 64, installed_base_apk_sha256='1' * 64,
            android_test_apk_sha256='2' * 64,
            debug_signing_certificate_sha256='3' * 64,
            physical_device_qualified=False, release_qualified=False)
        target.write_text(json.dumps(identity))
        return identity

    def test_identity_release_claim_refused(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'identity.json'
            identity = self.make_identity(path)
            em.validate_identity(path, 'a' * 40)
            identity['release_qualified'] = True
            path.write_text(json.dumps(identity))
            with self.assertRaises(RuntimeError):
                em.validate_identity(path, 'a' * 40)

    def test_independent_receipt_cannot_forge_results(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            identity_path = folder / 'identity.json'
            self.make_identity(identity_path)
            report = {
                'schema_version': 1,
                'producer': 'cinderbox-m25-profile-hosted-emulator',
                'overall': 'PASS_M25_PROFILE_HOSTED_EMULATOR',
                'source_sha': 'a' * 40, 'run_id': '1234',
                'test_class': em.TEST_CLASS, 'test_count': 4, 'android_api': 36,
                'hosted_emulator_only': True, 'physical_device_qualified': False,
                'release_qualified': False, 'publication_allowed': False,
                'automatic_game_update': False, 'raw_logs_retained': False,
                'summary': em.summary(self.response(), 0),
                'app_apk_sha256': '1' * 64, 'android_test_apk_sha256': '2' * 64,
            }
            evidence = folder / 'M25_PROFILE_EMULATOR_EVIDENCE.json'
            evidence.write_text(json.dumps(report))
            self.assertEqual(m25_verify.verify(folder, identity_path, 'a' * 40, '1234')
                ['tests_verified'], 4)
            report['summary']['passed_tests'] = report['summary']['passed_tests'][:-1]
            evidence.write_text(json.dumps(report))
            with self.assertRaises(AssertionError):
                m25_verify.verify(folder, identity_path, 'a' * 40, '1234')


if __name__ == '__main__':
    unittest.main()
