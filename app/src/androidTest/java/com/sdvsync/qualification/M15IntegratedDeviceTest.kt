package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.diagnostics.CenterStatus
import com.sdvsync.diagnostics.OperationCenterPolicy
import com.sdvsync.download.GameDownloadRecovery
import com.sdvsync.local.InstallHealth
import com.sdvsync.local.InstallationScanner
import com.sdvsync.local.StoragePlanner
import com.sdvsync.mods.BatchModEntry
import com.sdvsync.mods.ModBatchTransaction
import com.sdvsync.saves.SaveRestoreTransaction
import java.io.File
import java.nio.file.Files
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * M15 crosses real runtime component boundaries, unlike M14's isolated-unit lane.
 * All writes are inside a fresh, owned canonical cache fixture. No Steam login,
 * UI-driven storage authorization, app filesDir, external game or save is touched.
 * Instrumentation invokes ONLY this class; M14 device tests are not repeated.
 */
@RunWith(AndroidJUnit4::class)
class M15IntegratedDeviceTest {
    private lateinit var root: File
    private lateinit var journals: File

    @Before fun setUp() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val cache = context.cacheDir.canonicalFile
        check(cache.isDirectory && cache.canWrite()) { "Canonical app cache unavailable" }
        root = Files.createTempDirectory(cache.toPath(), "m15-device-").toFile().canonicalFile
        check(root.parentFile == cache && root.name.startsWith("m15-device-")) { "Fixture escaped cache" }
        var ancestor: File? = root
        while (ancestor != null) {
            check(!Files.isSymbolicLink(ancestor.toPath())) { "Symlink ancestor" }
            ancestor = ancestor.parentFile
        }
        journals = File(root, "journals").apply { check(mkdir()) }
        check(File(root, ".m15-owned").createNewFile())
    }

    @After fun tearDown() {
        if (!::root.isInitialized) return
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        check(root.canonicalFile.parentFile == cache && root.name.startsWith("m15-device-") &&
            File(root, ".m15-owned").isFile && !Files.isSymbolicLink(root.toPath())) {
            "Refuse to delete a non-owned fixture"
        }
        assertTrue("Could not clean the M15 fixture", root.deleteRecursively())
    }

    @Test fun interruptedModInstallLeavesDownloadCheckpointAndSaveUntouched() {
        val game = File(root, "game").apply { check(mkdir()) }
        val recovery = GameDownloadRecovery(journals)
        recovery.beginNew(game, "public", "linux", true)
        val save = File(root, "live-save").apply { check(mkdir()) }
        File(save, "keep.txt").writeText("do-not-change")

        val mods = File(root, "Mods").apply { check(mkdir()) }
        File(mods, "alpha").apply { check(mkdir()) }
        File(mods, "alpha/original.txt").writeText("original")
        val incoming = File(root, "incoming").apply { check(mkdir()) }
        val alpha = File(incoming, "alpha").apply { check(mkdir()) }
        File(alpha, "replacement.txt").writeText("replacement")
        val beta = File(incoming, "beta").apply { check(mkdir()) }
        File(beta, "new.txt").writeText("new")
        val transaction = ModBatchTransaction(journals, mods)
        try {
            transaction.install(listOf(BatchModEntry("alpha", alpha), BatchModEntry("beta", beta)),
                snapshot = {}, afterStep = { index -> if (index == 0) error("M15 injected interruption") })
            fail("Injected failure did not interrupt mod installation")
        } catch (_: IllegalStateException) { }

        assertTrue(transaction.recover())
        assertEquals("original", File(mods, "alpha/original.txt").readText())
        assertFalse(File(mods, "alpha/replacement.txt").exists())
        assertFalse(File(mods, "beta").exists())
        assertEquals("do-not-change", File(save, "keep.txt").readText())
        GameDownloadRecovery(journals).requireMatching(game, "public", "linux", true)
        assertNotNull(GameDownloadRecovery(journals).pending())
        recovery.discard()
    }

    @Test fun saveRestorePreservesCustomFilesAndUnrelatedDownloadState() {
        val game = File(root, "game").apply { check(mkdir()) }
        GameDownloadRecovery(journals).beginNew(game, "beta", "windows", false)
        val backup = File(root, "backup").apply { check(mkdir()) }
        File(backup, "SaveGameInfo").writeText("restored")
        val live = File(root, "live").apply { check(mkdir()) }
        File(live, "SaveGameInfo").writeText("before")
        File(live, "custom.txt").writeText("keep")

        assertTrue(SaveRestoreTransaction(journals).restore(backup, live))
        assertEquals("restored", File(live, "SaveGameInfo").readText())
        assertEquals("keep", File(live, "custom.txt").readText())
        assertTrue(SaveRestoreTransaction(journals).recover())
        GameDownloadRecovery(journals).requireMatching(game, "beta", "windows", false)
        GameDownloadRecovery(journals).discard()
    }

    @Test fun corruptSaveJournalFailsClosedWithoutCrossFeatureMutation() {
        val game = File(root, "game").apply { check(mkdir()) }
        GameDownloadRecovery(journals).beginNew(game, "public", "macos", false)
        val backup = File(root, "backup").apply { check(mkdir()) }
        File(backup, "SaveGameInfo").writeText("unwanted")
        val live = File(root, "live").apply { check(mkdir()) }
        File(live, "SaveGameInfo").writeText("original")
        File(journals, "m11-save-restore.properties").writeText("untrusted-record")
        assertFalse(SaveRestoreTransaction(journals).recover())
        try {
            SaveRestoreTransaction(journals).restore(backup, live)
            fail("Corrupt journal was silently bypassed")
        } catch (_: IllegalStateException) { }
        assertEquals("original", File(live, "SaveGameInfo").readText())
        assertTrue(File(journals, "m11-save-restore.properties").exists())
        GameDownloadRecovery(journals).requireMatching(game, "public", "macos", false)
        GameDownloadRecovery(journals).discard()
    }

    @Test fun partialInstallationAndUnknownSizeCannotBecomeGreenLight() {
        val incomplete = File(root, "partial-game").apply { check(mkdir()) }
        File(incomplete, "Stardew Valley.dll").writeText("partial")
        val before = File(incomplete, "Stardew Valley.dll").readBytes()
        val assessment = InstallationScanner.game(incomplete)
        assertEquals(InstallHealth.INCOMPLETE, assessment.health)
        assertFalse(assessment.usable)
        val budget = StoragePlanner.downloadPlan(incomplete, null)
        assertNull(budget.payloadBytes)
        assertNull(budget.requiredBytes)
        assertFalse(budget.sufficient == true)
        assertArrayEquals(before, File(incomplete, "Stardew Valley.dll").readBytes())
    }

    @Test fun conflictingOperationsShowGuidanceWithoutActingOnFiles() {
        val userFile = File(root, "keep.json").apply { writeText("fixture-private") }
        val cards = OperationCenterPolicy.build(
            "ERROR", "REVIEW_REQUIRED", false, false, false, true,
            setOf("download", "mod_batch", "save_restore"), listOf("CONFLICT"))
        assertEquals(cards.size, cards.map { it.id }.toSet().size)
        for (id in listOf("download", "mod_batch", "save_restore", "mod_review", "sync")) {
            val card = cards.single { it.id == id }
            assertEquals(CenterStatus.ACTION_REQUIRED, card.status)
            assertFalse(card.detail.contains("fixture-private"))
            assertFalse(card.action.isBlank())
        }
        assertEquals("fixture-private", userFile.readText())
    }

    @Test fun symlinkedInstallationIsNotAcceptedOrRewritten() {
        val actual = File(root, "real-game").apply { check(mkdir()) }
        File(actual, "keep").writeText("untouched")
        val alias = File(root, "linked-game")
        Files.createSymbolicLink(alias.toPath(), actual.toPath())
        assertEquals(InstallHealth.INACCESSIBLE, InstallationScanner.game(alias).health)
        assertFalse(StoragePlanner.downloadPlan(alias, null).sufficient == true)
        assertEquals("untouched", File(actual, "keep").readText())
    }
}
