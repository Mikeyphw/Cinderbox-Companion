package com.sdvsync.qualification

import android.os.SystemClock
import android.content.pm.PackageManager
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.local.InstallHealth
import com.sdvsync.local.InstallationScanner
import com.sdvsync.steam.SteamCloudService
import com.sdvsync.steam.SteamClientManager
import com.sdvsync.steam.SteamSessionStore
import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.koin.core.context.GlobalContext

/** M21 U: user-visible offline workflows, not another M17/M20 lifecycle rerun. */
@RunWith(AndroidJUnit4::class)
class M21UWorkflowDeviceTest {
    @get:Rule val activity = createAndroidComposeRule<MainActivity>()
    private fun enterOffline() {
        activity.onNodeWithText("Continue offline").performScrollTo().performClick()
        activity.waitForIdle()
    }
    @Test fun u01OfflineSavesTabVisible() {
        enterOffline()
        activity.onNodeWithText("Saves").assertExists()
    }
    @Test fun u02OfflineModsTabNavigation() {
        enterOffline()
        activity.onNodeWithText("Mods").performClick()
        activity.waitForIdle()
        activity.onNodeWithText("Backups").assertExists()
    }
    @Test fun u03OfflineDownloadsTabNavigation() {
        enterOffline()
        activity.onNodeWithText("Download").performClick()
        activity.waitForIdle()
        activity.onNodeWithText("Download Game").assertExists()
    }
    @Test fun u04InstallationHealthReadOnlyFromSettings() {
        activity.onNodeWithText("Continue offline").assertExists()
        activity.onNodeWithText("Settings").performScrollTo().performClick()
        activity.waitForIdle()
        activity.onNodeWithText("Inspect game, Cinderbox, SMAPI and storage")
            .performScrollTo().performClick()
        activity.waitForIdle()
        activity.onNodeWithText("Read-only checks. Detection is not cryptographic integrity verification.")
            .assertIsDisplayed()
    }
}

/** M21 T: real opt-in authenticated Steam API checks. Never login/logout or write Cloud files. */
@RunWith(AndroidJUnit4::class)
class M21TAuthenticatedDeviceTest {
    @get:Rule val activity = createAndroidComposeRule<MainActivity>()
    private fun requireConsent() {
        assertEquals("true", InstrumentationRegistry.getArguments().getString("m21_auth_opt_in"))
    }
    private fun client(): SteamClientManager = GlobalContext.get().get()
    private fun requireConnected(): SteamClientManager {
        requireConsent()
        val mgr = client()
        repeat(90) {
            if (mgr.isLoggedIn) return mgr
            SystemClock.sleep(500)
        }
        check(mgr.isLoggedIn) { "M21_AUTHENTICATED_TRANSPORT_NOT_READY" }
        return mgr
    }
    @Test fun t01ExistingEncryptedSteamSessionPresent() {
        requireConsent()
        val store: SteamSessionStore = GlobalContext.get().get()
        assertTrue("M21_SAVED_SESSION_REQUIRED", store.hasSession())
    }
    @Test fun t02AuthenticatedSteamConnectionLive() {
        assertTrue("M21_LIVE_STEAM_CONNECTION_REQUIRED", requireConnected().isLoggedIn)
    }
    @Test fun t03SteamLicenseCallbackAvailable() {
        val mgr = requireConnected()
        assertNotNull(mgr.licenses.value) // Actual Steam callback state, no account details in report.
        assertTrue("M21_LICENSE_LIST_REQUIRED", mgr.licenses.value.isNotEmpty())
    }
    @Test fun t04SteamCloudMetadataReadOnlyRequest() {
        requireConnected()
        val cloud: SteamCloudService = GlobalContext.get().get()
        // Steam Cloud enumeration is a genuine authenticated read-only API call.
        // Never list filenames, Steam IDs, usernames or any save bytes in test output.
        val received = runBlocking { withTimeout(45_000) { cloud.listCloudFiles() } }
        assertNotNull(received) // An account with no cloud saves is valid.
    }
}

/** M21 I: fixture-only detection and real same-signer, replace-in-place APK data persistence. */
@RunWith(AndroidJUnit4::class)
class M21IInstallationDeviceTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun id(): String {
        val nonce = InstrumentationRegistry.getArguments().getString("m21_nonce") ?: ""
        require(Regex("[0-9a-f]{32}").matches(nonce)) { "M21_NONCE_INVALID" }
        return MessageDigest.getInstance("SHA-256").digest(nonce.toByteArray())
            .joinToString("") { "%02x".format(it) }.take(24)
    }
    private fun fixture(): File {
        val base = context.cacheDir.canonicalFile
        check(base.isDirectory && base.canWrite())
        val dest = File(base, "m21-installed-check-${id()}")
        check(!dest.exists() && dest.mkdir())
        return dest
    }
    @Test fun i01MissingGameNotAcceptedAsInstalled() {
        val f = fixture()
        try { assertEquals(InstallHealth.MISSING, InstallationScanner.game(f).health) }
        finally { assertTrue(f.delete()) }
    }
    @Test fun i02PartialGameFilesNeverMarkedUsable() {
        val f = fixture()
        try {
            File(f, "Stardew Valley.dll").writeText("incomplete")
            assertFalse(InstallationScanner.game(f).usable)
        } finally {
            assertTrue(File(f, "Stardew Valley.dll").delete())
            assertTrue(f.delete())
        }
    }
    @Test fun i03SyntheticCoreStructureDetectedNotHashVerified() {
        val f = fixture()
        val names = listOf("Stardew Valley.dll", "StardewValley.GameData.dll", "BmFont.dll",
            "xTile.dll", "Lidgren.Network.dll")
        try {
            names.forEach { File(f, it).writeText("synthetic") }
            check(File(f, "Content").mkdir())
            File(f, "Content/synthetic.dat").writeText("synthetic")
            assertEquals(InstallHealth.STRUCTURALLY_VALID, InstallationScanner.game(f).health)
        } finally {
            assertTrue(File(f, "Content/synthetic.dat").delete())
            assertTrue(File(f, "Content").delete())
            names.forEach { assertTrue(File(f, it).delete()) }
            assertTrue(f.delete())
        }
    }
    private fun marker(): File = File(context.filesDir.canonicalFile, "m21-upgrade-owned-${id()}")
    @Test fun i04SeedOwnedUpgradeMarker() {
        val file=marker()
        check(!file.exists()) { "M21_UPGRADE_MARKER_COLLISION" }
        check(file.createNewFile())
        file.writeText("m21-test-only-${id()}")
        assertEquals("m21-test-only-${id()}", file.readText())
    }
    @Test fun i05VerifyUpgradePreservesPrivateStateAndCleanup() {
        val file=marker()
        assertTrue("M21_UPGRADE_DATA_MISSING", file.isFile && !java.nio.file.Files.isSymbolicLink(file.toPath()))
        assertEquals("m21-test-only-${id()}", file.readText())
        assertTrue("M21_UPGRADE_FIXTURE_CLEANUP_FAILED", file.delete())
    }
    @Test fun i06InstalledCinderboxPackageRecognized() {
        // Only read PackageManager; NEVER install/uninstall com.game.cinderbox.
        try { assertNotNull(context.packageManager.getPackageInfo("com.game.cinderbox", 0)) }
        catch (_: PackageManager.NameNotFoundException) {
            throw IllegalStateException("M21_REAL_CINDERBOX_INSTALL_NOT_PRESENT")
        }
    }
}
