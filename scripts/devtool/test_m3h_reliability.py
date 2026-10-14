"""Static M3H regressions. Android JVM/Gradle tests run separately in Devtool CI."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class M3HReliabilitySourceContracts(unittest.TestCase):
    def test_retry_owner_is_not_the_individual_auth_job(self):
        runner = read("app/src/main/java/com/sdvsync/steam/SavedSessionReconnectRunner.kt")
        auth = read("app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt")
        self.assertIn("supervisorScope {", runner)
        self.assertIn("launch {", runner)
        self.assertIn("}.join()", runner)
        self.assertIn("1..6", runner)
        self.assertIn("30_000L", runner)
        self.assertIn("runSavedSessionReconnect(", auth)
        self.assertIn("attempt = { loginWithSavedSession() }", auth)
        self.assertNotIn("repeat(6) { index ->", auth)
        self.assertIn("SavedSessionReconnectRunnerTest", read("app/src/test/java/com/sdvsync/steam/SavedSessionReconnectRunnerTest.kt"))

    def test_no_recovery_after_logout_or_while_manual_auth_is_active(self):
        auth = read("app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt")
        self.assertIn("isUserDisconnect || !sessionStore.hasSession()", auth)
        self.assertIn("authAttempts.activeAttempt() != null", auth)
        self.assertIn("autoReconnectJob?.cancel()", auth)
        self.assertIn("reconnect_exhausted", auth)
        self.assertIn("reconnect_attempt_${number}_failed", auth)

    def test_foreground_and_network_resumption(self):
        auth = read("app/src/main/java/com/sdvsync/steam/SteamAuthenticator.kt")
        activity = read("app/src/main/java/com/sdvsync/MainActivity.kt")
        self.assertIn("registerDefaultNetworkCallback(networkCallback)", auth)
        self.assertIn("unregisterNetworkCallback(networkCallback)", auth)
        self.assertIn("NetworkCapabilities.NET_CAPABILITY_VALIDATED", auth)
        self.assertIn("onAppForeground()", activity)
        self.assertIn("onAppBackground()", activity)
        self.assertIn("requestSavedSessionRecovery(\"network_restored\")", auth)
        self.assertIn("reconnectWakeups.trySend(Unit)", auth)

    def test_depot_percent_not_published_as_game_percent(self):
        service = read("app/src/main/java/com/sdvsync/download/GameDownloadService.kt")
        manager = read("app/src/main/java/com/sdvsync/download/GameDownloadManager.kt")
        screen = read("app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt")
        self.assertNotIn("overallPercent = depotPercentComplete", service)
        self.assertNotIn("totalBytes = depotBytes.values.sum()", service)
        self.assertIn("currentDepotPercent = depotPercent", service)
        self.assertIn("filesDownloaded = completedFiles.size", service)
        self.assertIn("it.copy(state = DownloadState.DOWNLOADING)", service)
        self.assertIn("maxOf(current.downloadedBytes, totalDownloaded)", service)
        self.assertIn("val currentDepotId: Int? = null", manager)
        self.assertIn("val filesDownloaded: Int = 0", manager)
        self.assertIn("not overall game progress", screen)
        self.assertIn("Files received: $filesDownloaded", screen)

    def test_original_m3g_regression_updated_for_new_owner(self):
        tests = read("scripts/devtool/test_m3g_steam_reliability.py")
        self.assertIn("runner = read('app/src/main/java/com/sdvsync/steam/SavedSessionReconnectRunner.kt')", tests)
        self.assertIn("self.assertIn('supervisorScope', runner)", tests)

if __name__ == "__main__":
    unittest.main()
