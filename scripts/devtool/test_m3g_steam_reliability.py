"""Source-bound M3G contract tests. CI must also run Gradle/Android tests."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

def read(relative):
    return (ROOT / relative).read_text()

class M3GSourceContracts(unittest.TestCase):
    def test_machine_id_initialized_before_koin(self):
        source = read('app/src/main/java/com/sdvsync/SdvSyncApp.kt')
        self.assertLess(source.index('AndroidSteamMachineId.initialize(this)'), source.index('startKoin {'))

    def test_android_identity_persisted_and_private(self):
        source = read('app/src/main/java/com/sdvsync/steam/AndroidSteamMachineId.kt')
        self.assertIn('Context.MODE_PRIVATE', source)
        self.assertIn('UUID.randomUUID()', source)
        self.assertIn('.commit()', source)
        self.assertIn('getMachineId(): ByteArray', source)
        self.assertNotIn('Runtime.getRuntime()', source)
        self.assertNotIn('lshal', source)

    def test_jar_instrumentation_applies_to_dependencies(self):
        build = read('app/build.gradle.kts')
        self.assertIn('InstrumentationScope.ALL', build)
        self.assertIn('AndroidSafeMachineIdVisitorFactory::class.java', build)

    def test_vendor_method_abi_and_fail_closed(self):
        visitor = read('buildSrc/src/main/kotlin/com/sdvsync/build/AndroidSafeMachineIdVisitorFactory.kt')
        self.assertIn('name == "getMachineID" && descriptor == "()[B"', visitor)
        self.assertIn('"com/sdvsync/steam/AndroidSteamMachineId"', visitor)
        self.assertIn('check(didRewrite)', visitor)
        self.assertIn('return null', visitor)
        self.assertNotIn('"lshal"', visitor)

    def test_no_network_veto(self):
        auth = read('app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt')
        block = auth.split('private suspend fun connectOrFail(', 1)[1].split('private suspend fun runAuthAttempt(', 1)[0]
        self.assertNotIn('return false\n        }\n        if (!isClockValid', block)
        self.assertIn('network_capabilities_unavailable', block)
        self.assertIn('connectWithTimeout()', block)

    def test_reconnect_bounded_and_cancelable(self):
        auth = read('app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt')
        self.assertIn('repeat(6)', auth)
        self.assertIn('30_000L', auth)
        self.assertIn('autoReconnectJob?.cancel()', auth)
        self.assertIn('loginWithSavedSession()', auth)
        self.assertIn('reconnect_exhausted', auth)

    def test_transport_failure_reasons(self):
        transport = read('app/src/main/java/com/sdvsync/steam/transport/StableWebSocketConnection.kt')
        for label in ['websocket_close_code_', 'websocket_stream_ended', 'websocket_timeout', 'websocket_exception', 'websocket_send_exception']:
            self.assertIn(label, transport)
        self.assertIn('20.toDuration(DurationUnit.SECONDS)', transport)
        self.assertIn('expectedGeneration = generation', transport)

    def test_connection_events(self):
        manager = read('app/src/main/java/com/sdvsync/steam/SteamClientManager.kt')
        for event in ['cm_connect_started', 'cm_transport_connected', 'steam_logon_ok', 'transport_closed_unexpectedly']:
            self.assertIn(event, manager)

    def test_bounded_private_diagnostics(self):
        diag = read('app/src/main/java/com/sdvsync/steam/SteamDiagnostics.kt')
        self.assertIn('MAX_EVENTS = 180', diag)
        self.assertIn('HISTORY_MS = 3_600_000L', diag)
        self.assertIn('steam_diagnostics_history', diag)
        self.assertIn('takeLast(MAX_EVENTS)', diag)
        self.assertIn('fun exportJson()', diag)
        self.assertNotIn('password', diag.lower())
        self.assertNotIn('getssid', diag.lower())
        self.assertNotIn('refreshtoken', diag.lower())

    def test_live_badge_in_every_topbar(self):
        topbar = read('app/src/main/java/com/sdvsync/ui/components/StardewTopAppBar.kt')
        self.assertIn('SteamLiveBadge()', topbar)
        badge = read('app/src/main/java/com/sdvsync/ui/components/SteamLiveBadge.kt')
        self.assertIn('snapshot.collectAsState()', badge)
        self.assertIn('loginWithSavedSession()', badge)

    def test_hidden_diagnostics_and_unlock(self):
        settings = read('app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt')
        self.assertIn('developerTaps >= 7', settings)
        self.assertIn('onOpenDeveloperDiagnostics', settings)
        nav = read('app/src/main/java/com/sdvsync/MainActivity.kt')
        self.assertIn('composable("steam_diagnostics")', nav)

    def test_one_hour_graph_and_saf_export(self):
        screen = read('app/src/main/java/com/sdvsync/ui/screens/SteamDiagnosticsScreen.kt')
        self.assertIn('minuteHistory(now)', screen)
        self.assertIn('CreateDocument("application/json")', screen)
        self.assertIn('SteamDiagnostics.exportJson()', screen)
        self.assertIn('Spacer', screen)

    def test_no_published_release_not_reported_as_error(self):
        checker = read('app/src/main/java/com/sdvsync/download/GitHubReleaseChecker.kt')
        self.assertIn('AppLogger.i(TAG, "No published GitHub releases for $repo")', checker)
        self.assertNotIn('AppLogger.e(TAG, "No releases found for $repo")', checker)

    def test_no_unsafe_operational_scope(self):
        changed = [
            read('app/src/main/java/com/sdvsync/steam/AndroidSteamMachineId.kt'),
            read('app/src/main/java/com/sdvsync/steam/SteamDiagnostics.kt'),
            read('app/src/main/java/com/sdvsync/ui/screens/SteamDiagnosticsScreen.kt')
        ]
        for content in changed:
            self.assertNotIn('su -c', content)
            self.assertNotIn('chmod ', content)
            self.assertNotIn('disable SELinux', content)

if __name__ == '__main__':
    unittest.main()
