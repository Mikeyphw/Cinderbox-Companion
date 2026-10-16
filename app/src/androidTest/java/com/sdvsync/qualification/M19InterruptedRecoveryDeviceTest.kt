package com.sdvsync.qualification

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.diagnostics.CenterStatus
import com.sdvsync.diagnostics.OperationCenterPolicy
import com.sdvsync.download.GameDownloadRecovery
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/**
 * M19: genuine process stop between production download-checkpoint stages.
 * Entirely synthetic bytes and app-private, nonce-namespaced test paths.
 * No Steam network, credentials, real game directories, mods, saves, or backups.
 * Host runner performs the force-stop; instrumentation must not terminate itself.
 */
@RunWith(AndroidJUnit4::class)
class M19InterruptedRecoveryDeviceTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private data class Fixture(val root: File, val journalRoot: File, val dest: File)

    private fun fixture(): Fixture {
        val nonce = InstrumentationRegistry.getArguments().getString("m19_nonce") ?: ""
        require(Regex("[0-9a-f]{32}").matches(nonce)) { "M19_NONCE_INVALID" }
        val hash = MessageDigest.getInstance("SHA-256")
            .digest(nonce.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }.take(24)
        val root = File(InstrumentationRegistry.getInstrumentation().targetContext.filesDir,
            "m19-test-only-$hash")
        require(!root.isDirectory || !java.nio.file.Files.isSymbolicLink(root.toPath())) {
            "M19_FIXTURE_UNSAFE"
        }
        return Fixture(root, File(root, "checkpoint"), File(root, "game"))
    }

    private fun testBytes(): ByteArray = ByteArray(4096) { i -> ((i * 37 + 19) and 0xff).toByte() }

    private fun partial(f: Fixture) = File(f.dest, "synthetic-partial.bin")

    private fun assertSignedOut() {
        rule.onNodeWithText("Continue offline").assertExists()
    }

    @Test fun seedInterruptedDownloadCheckpoint() {
        assertSignedOut()
        val f = fixture()
        // A fresh random fixture must not preexist: never overwrite unknown files.
        assertFalse("Fixture collision", f.root.exists())
        assertTrue("Private fixture mkdir", f.root.mkdir())
        val recovery = GameDownloadRecovery(f.journalRoot)
        recovery.beginNew(f.dest, "public", "linux", true)
        assertTrue("Write synthetic partial data", partial(f).createNewFile())
        partial(f).writeBytes(testBytes())
        assertArrayEquals(testBytes(), partial(f).readBytes())
        assertNotNull("Production checkpoint must be present", recovery.pending())
        recovery.requireMatching(f.dest, "public", "linux", true)
    }

    @Test fun verifyInterruptedCheckpointAndReviewAfterColdRelaunch() {
        assertSignedOut()
        val f = fixture()
        val recovery = GameDownloadRecovery(f.journalRoot)
        // Preserve the isolated fixture on ANY assertion failure: it is
        // diagnostic evidence. Cleanup occurs only after all checks succeed.
        // This data was committed by the previous, now-terminated process.
        assertTrue("Owned fixture must survive process stop", f.root.isDirectory)
        assertArrayEquals("Partial bytes must not change", testBytes(), partial(f).readBytes())
        val checkpoint = recovery.pending()
        assertNotNull("Journal must survive process death", checkpoint)
        assertTrue("Ownership marker must survive", checkpoint!!.matches(f.dest, "public", "linux", true))
        recovery.requireMatching(f.dest, "public", "linux", true)

        // Explicit matching recovery is possible, but silent wrong-option or
        // second-download starts must fail closed and keep partial bytes intact.
        var mismatchRejected = false
        try { recovery.requireMatching(f.dest, "beta", "linux", true) }
        catch (_: IllegalStateException) { mismatchRejected = true }
        assertTrue("Different Steam branch must be rejected", mismatchRejected)
        var duplicateRejected = false
        try { recovery.beginNew(f.dest, "public", "linux", true) }
        catch (_: IllegalStateException) { duplicateRejected = true }
        assertTrue("Duplicate operation must be rejected", duplicateRejected)
        assertArrayEquals("Guard failures must not alter partial data", testBytes(), partial(f).readBytes())

        // Production Operation Center policy must show an explicit review
        // requirement rather than a fake success or automatic retry.
        val cards = OperationCenterPolicy.build(
            gameState = "IDLE", modState = "IDLE", smapiActive = false,
            smapiError = false, appDownloadActive = false, pendingReview = false,
            journals = setOf("download"), syncOutcomes = emptyList()
        )
        val card = cards.single { it.id == "download" }
        assertEquals(CenterStatus.ACTION_REQUIRED, card.status)
        assertEquals("Open Downloads", card.action)
        assertTrue(card.detail.contains("before resuming"))
        assertFalse(cards.any { it.id == "download" && it.status == CenterStatus.COMPLETED })

        // Discard is explicit and keeps partial game bytes; it never resumes a job.
        recovery.discard()
        assertNull(recovery.pending())
        assertArrayEquals(testBytes(), partial(f).readBytes())
        // Cleanup strictly this nonce-namespaced disposable fixture. Never
        // recursively delete a user-supplied path or unrelated app state.
        // If unexpected contents appear, leave them for inspection and FAIL.
        val journal = File(f.journalRoot, "m6-game-download.properties")
        val session = File(f.dest, ".cinderbox-download.session")
        val part = partial(f)
        val expected = listOf(part, session, journal)
        fun children(dir: File): Set<String> = dir.list()?.toSet() ?: emptySet()
        if (f.root.exists()) {
            val safe = f.root.isDirectory && !java.nio.file.Files.isSymbolicLink(f.root.toPath()) &&
                children(f.root).all { it in setOf("checkpoint", "game") } &&
                (!f.dest.exists() || children(f.dest).all { it in setOf(part.name, session.name) }) &&
                (!f.journalRoot.exists() || children(f.journalRoot).all { it == journal.name }) &&
                expected.filter { it.exists() }.all { it.isFile && !java.nio.file.Files.isSymbolicLink(it.toPath()) }
            if (!safe) fail("M19_FIXTURE_CLEANUP_BLOCKED")
            for (file in expected) if (file.exists()) assertTrue("Fixture file removal", file.delete())
            if (f.dest.exists()) assertTrue("Fixture game removal", f.dest.delete())
            if (f.journalRoot.exists()) assertTrue("Fixture journal removal", f.journalRoot.delete())
            assertTrue("Private fixture removal", f.root.delete())
        }
    }
}
