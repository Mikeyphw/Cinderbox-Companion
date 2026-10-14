#!/usr/bin/env python3
"""M3F static regression contracts; Android JUnit tests run in Gradle CI."""
import unittest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt'
CLIENT = ROOT / 'app/src/main/java/com/sdvsync/steam/SteamClientManager.kt'
FACTORY_TEST = ROOT / 'app/src/test/java/com/sdvsync/steam/SteamConnectionFactoryTest.kt'
POLICY_TEST = ROOT / 'app/src/test/java/com/sdvsync/steam/SteamAuthRecoveryTest.kt'
STRINGS = ROOT / 'app/src/main/res/values/strings.xml'

class SteamAuthRecoverySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth = AUTH.read_text()
        cls.client = CLIENT.read_text()
        cls.tests = FACTORY_TEST.read_text()
        cls.policy = POLICY_TEST.read_text()
        cls.resources = STRINGS.read_text()

    def test_code_submission_is_bounded(self):
        self.assertIn('withTimeout(STEAM_GUARD_TIMEOUT_MS)', self.auth)
        self.assertIn('sendSteamGuardCode(code, confirmationType, attemptScope).await()', self.auth)

    def test_credential_begin_is_bounded(self):
        self.assertIn('withTimeout(AUTH_REQUEST_TIMEOUT_MS)', self.auth)

    def test_polling_is_bounded(self):
        self.assertIn('withTimeout(AUTH_POLL_TIMEOUT_MS)', self.auth)
        self.assertEqual(self.auth.count('pollUntilResultBounded('), 5)

    def test_final_callback_is_bounded(self):
        self.assertIn('withTimeout(LOGON_CALLBACK_TIMEOUT_MS) { callbackResult.await() }', self.auth)

    def test_timeouts_generate_errors_before_generic_cancellation(self):
        # Check the three M3F authentication handlers by purpose, not by a
        # global catch count: connectOrFail() already has a timeout handler.
        # That unrelated existing handler made the original count=3 fail.
        for message in (
            'Saved session login timed out',
            'Steam credential authentication timed out',
            'Steam QR authentication timed out',
        ):
            pattern = (r'} catch \(_: TimeoutCancellationException\) \{\s+'
                       r'AppLogger\.w\(TAG, "' + re.escape(message) + r'"\)')
            self.assertRegex(self.auth, pattern)
        self.assertIn('R.string.error_steam_verification_timeout', self.auth)

    def test_timeout_forces_clean_transport(self):
        self.assertEqual(self.auth.count('AppLogger.w(TAG, "Steam credential authentication timed out")'), 1)
        self.assertIn('AppLogger.w(TAG, "Steam QR authentication timed out")', self.auth)
        for marker in ['Saved session login timed out', 'Steam credential authentication timed out', 'Steam QR authentication timed out']:
            portion = self.auth[self.auth.index(marker):]
            self.assertLess(portion.index('clientManager.disconnect()'), 260)

    def test_orphaned_spinner_has_fallback(self):
        self.assertIn('shouldRecoverOrphanedAuthState(currentAuthState)', self.auth)
        self.assertIn('_authState.value = AuthState.Error(context.getString(R.string.error_steam_disconnected_login))', self.auth)

    def test_orphan_policy_is_pure(self):
        self.assertIn('internal fun shouldRecoverOrphanedAuthState(state: AuthState)', self.auth)
        self.assertIn('state.isTransientAttemptState()', self.auth)
        self.assertIn('assertFalse(shouldRecoverOrphanedAuthState(AuthState.LoggedIn))', self.policy)

    def test_websocket_is_first(self):
        ordering = self.client[self.client.index('return buildList(2)'):]
        self.assertLess(ordering.index('add(preferredWebSocket)'), ordering.index('preferredTcp?.let(::add)'))

    def test_tcp_is_still_supported(self):
        self.assertIn('EnumSet.of(ProtocolTypes.TCP, ProtocolTypes.WEB_SOCKET)', self.client)
        self.assertIn('IConnectionFactory.DEFAULT.createConnection(', self.client)

    def test_no_improper_mid_session_fallback(self):
        self.assertIn('connectionPlan.clear()', self.client)
        self.assertIn('if (!userInitiated &&', self.client)

    def test_candidate_tests_updated(self):
        self.assertIn('falls back from websocket to TCP once', self.tests)
        self.assertIn('assertEquals(webSocketOne, plan.begin(', self.tests)
        self.assertIn('assertEquals(tcpOne, plan.retry())', self.tests)

    def test_steamguard_code_handling_intact(self):
        self.assertIn('previousCodeWasIncorrect = true', self.auth)
        self.assertIn('isCodeConfirmation()', self.auth)

    def test_errors_are_l10n_resources(self):
        self.assertIn('<string name="error_steam_verification_timeout">', self.resources)

    def test_no_sensitive_data_introduced_into_logs(self):
        self.assertNotIn('AppLogger.d(TAG, "Steam Guard code=', self.auth)
        self.assertNotIn('AppLogger.i(TAG, "Steam Guard code=', self.auth)

if __name__ == '__main__':
    unittest.main()
