"""M3H background network policy contract; behavioral coroutine tests run in Gradle."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class M3HBackgroundRecovery(unittest.TestCase):
    def test_network_wait_does_not_consume_attempts(self):
        s = source("app/src/main/java/com/sdvsync/steam/SavedSessionReconnectRunner.kt")
        self.assertIn("awaitNetwork: suspend () -> Unit = {}", s)
        self.assertIn("awaitNetwork()", s)
        self.assertLess(s.index("awaitNetwork()"), s.index("supervisorScope {"))
        a = source("app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt")
        self.assertIn("awaitNetwork = { awaitNetworkForReconnect() }", a)
        self.assertIn("reconnect_wait_for_network", a)
        self.assertIn("reconnect_network_available", a)
        self.assertIn("reconnectWakeups.receive()", a)
        self.assertIn("while (!isNetworkAvailable())", a)

    def test_foreground_started_by_visible_activity_only(self):
        a = source("app/src/main/java/com/sdvsync/MainActivity.kt")
        self.assertIn("Lifecycle.State.STARTED", a)
        self.assertIn("ConnectionState.LOGGED_IN", a)
        self.assertIn("SteamBackgroundService.start(this@MainActivity)", a)
        s = source("app/src/main/java/com/sdvsync/steam/SteamBackgroundService.kt")
        self.assertIn("ContextCompat.startForegroundService", s)
        self.assertIn("startForeground(NOTIFICATION_ID", s)
        self.assertIn("return START_NOT_STICKY", s)
        self.assertNotIn("START_STICKY", s.replace("START_NOT_STICKY", ""))
        auth = source("app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt")
        self.assertIn("SteamBackgroundService.stop(context)", auth)

    def test_user_control_and_ongoing_notification(self):
        s = source("app/src/main/java/com/sdvsync/steam/SteamBackgroundService.kt")
        for key in ("KEY_ENABLED", "fun setEnabled", "if (!enabled) stop(context)",
                    ".setOngoing(true)", "NotificationManager.IMPORTANCE_LOW"):
            self.assertIn(key, s)
        settings = source("app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt")
        self.assertIn("SteamBackgroundService.setEnabled(context, enabled)", settings)
        self.assertIn("Keep Steam connected in background", settings)

    def test_special_use_foreground_service_declared(self):
        manifest = source("app/src/main/AndroidManifest.xml")
        self.assertIn('android:name=".steam.SteamBackgroundService"', manifest)
        self.assertIn('android:foregroundServiceType="specialUse"', manifest)
        self.assertIn('android.permission.FOREGROUND_SERVICE_SPECIAL_USE', manifest)
        self.assertIn("android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE", manifest)
        self.assertIn('android:exported="false"', manifest)

    def test_coroutine_unit_regressions_present(self):
        k = source("app/src/test/java/com/sdvsync/steam/SavedSessionReconnectRunnerTest.kt")
        self.assertIn("network unavailability suspends without consuming attempts", k)
        self.assertIn("CompletableDeferred", k)
        self.assertIn("assertEquals(0, attempts)", k)

    def test_no_debug_secrets_or_unrelated_operations(self):
        new = source("app/src/main/java/com/sdvsync/steam/SteamBackgroundService.kt")
        for bad in ("accessToken", "refreshToken", "password", "Steam Guard", "Runtime.getRuntime", "su -c"):
            self.assertNotIn(bad, new)


if __name__ == "__main__":
    unittest.main()
