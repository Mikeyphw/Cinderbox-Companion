package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.diagnostics.CenterStatus
import com.sdvsync.diagnostics.OperationCenterPolicy
import com.sdvsync.download.GameDownloadRecovery
import com.sdvsync.local.StoragePlanner
import com.sdvsync.mods.BatchModEntry
import com.sdvsync.mods.ModBatchTransaction
import com.sdvsync.mods.ModProfileTransaction
import com.sdvsync.mods.ProfileFolderMove
import com.sdvsync.saves.SaveRestoreTransaction
import java.io.File
import java.nio.file.Files
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Explicit-only device lane. All mutations are restricted to a uniquely owned
 * targetContext.cacheDir fixture; never uses actual Saves, Mods or Steam data.
 * Recovery after process death is simulated by reopening the transaction object.
 */
@RunWith(AndroidJUnit4::class)
class M14IsolatedDeviceTest {
    private lateinit var root: File
    private lateinit var privateDir: File

    @Before fun setUp() {
        // Android can expose cacheDir through an alias (/data/user/0). Recovery
        // intentionally rejects symlink ancestors; use the exact same app-private
        // directory after resolving that platform-managed alias, not a weaker gate.
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        check(cache.isDirectory && cache.canWrite()) { "Canonical app cache unavailable" }
        root = Files.createTempDirectory(cache.toPath(), "m14-device-").toFile().canonicalFile
        check(root.parentFile == cache) { "Fixture escaped app-private cache" }
        var ancestor: File? = root
        while (ancestor != null) {
            check(!Files.isSymbolicLink(ancestor.toPath())) { "Fixture contains a symlink ancestor" }
            ancestor = ancestor.parentFile
        }
        privateDir = File(root, "journals").apply { check(mkdir()) }
        check(File(root, ".m14-test-owned").createNewFile())
    }

    @After fun tearDown() {
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        if (::root.isInitialized && root.parentFile?.canonicalFile == cache &&
            root.name.startsWith("m14-device-") &&
            File(root, ".m14-test-owned").isFile &&
            !Files.isSymbolicLink(root.toPath())) {
            assertTrue("Could not clean isolated M14 fixture", root.deleteRecursively())
        }
    }

    @Test fun checkpointResumeAndDiscard() {
        val dest = File(root, "game").apply { check(mkdir()) }
        val first = GameDownloadRecovery(privateDir)
        first.beginNew(dest, "public", "windows", true)
        val restarted = GameDownloadRecovery(privateDir)
        restarted.requireMatching(dest, "public", "windows", true)
        assertNotNull(restarted.pending())
        restarted.discard()
        assertNull(restarted.pending())
    }

    @Test fun crashStyleModProfileRollback() {
        val mods = File(root, "Mods").apply { check(mkdir()) }
        val original = File(mods, "alpha").apply { check(mkdir()) }
        File(original, "manifest.json").writeText("fixture-original")
        ModProfileTransaction(privateDir, mods).prepare(listOf(ProfileFolderMove("alpha", ".alpha")))
        assertTrue(original.renameTo(File(mods, ".alpha")))
        assertTrue(ModProfileTransaction(privateDir, mods).recover())
        assertEquals("fixture-original", File(original, "manifest.json").readText())
        assertFalse(File(mods, ".alpha").exists())
    }

    @Test fun modBatchFailureRollsBackMultipleChanges() {
        val mods = File(root, "Mods").apply { check(mkdir()) }
        val incoming = File(root, "incoming").apply { check(mkdir()) }
        val original = File(mods, "alpha").apply { check(mkdir()) }
        File(original, "old.txt").writeText("kept")
        val first = File(incoming, "alpha").apply { check(mkdir()) }
        File(first, "new.txt").writeText("new-alpha")
        val second = File(incoming, "beta").apply { check(mkdir()) }
        File(second, "new.txt").writeText("new-beta")
        val tx = ModBatchTransaction(privateDir, mods)
        // androidx.test.ext:junit 1.2.1 does not expose JUnit 4.13 assertThrows here.
        // Use the JUnit 4 fail/try/catch pattern instead; only the expected failure passes.
        try {
            tx.install(listOf(BatchModEntry("alpha", first), BatchModEntry("beta", second)),
                snapshot = {}, afterStep = { i -> if (i == 0) error("M14 simulated interruption") })
            fail("Expected the interrupted multi-mod transaction to fail")
        } catch (_: IllegalStateException) {
            // Transaction failure is expected; assertions below verify full rollback.
        }
        assertEquals("kept", File(mods, "alpha/old.txt").readText())
        assertFalse(File(mods, "alpha/new.txt").exists())
        assertFalse(File(mods, "beta").exists())
        assertTrue(tx.recover())
    }

    @Test fun corruptModJournalCannotAffectDownloadCheckpoint() {
        val mods = File(root, "Mods").apply { check(mkdir()) }
        val dest = File(root, "game").apply { check(mkdir()) }
        val recovery = GameDownloadRecovery(privateDir)
        recovery.beginNew(dest, "public", "linux", false)
        val corrupt = File(privateDir, "m9-mod-batch.properties")
        corrupt.writeText("invalid fixture journal")
        assertFalse(ModBatchTransaction(privateDir, mods).recover())
        recovery.requireMatching(dest, "public", "linux", false)
        assertTrue(corrupt.exists())
        recovery.discard()
    }

    @Test fun saveRestorePreservesOtherFiles() {
        val source = File(root, "backup").apply { check(mkdir()) }
        File(source, "SaveGameInfo").writeText("new")
        val target = File(root, "save").apply { check(mkdir()) }
        File(target, "SaveGameInfo").writeText("old")
        File(target, "custom.json").writeText("user-content")
        val transaction = SaveRestoreTransaction(privateDir)
        assertTrue(transaction.restore(source, target))
        assertEquals("new", File(target, "SaveGameInfo").readText())
        assertEquals("user-content", File(target, "custom.json").readText())
        assertTrue(SaveRestoreTransaction(privateDir).recover())
    }

    @Test fun corruptSaveJournalPreservesLiveSave() {
        val live = File(root, "save").apply { check(mkdir()) }
        File(live, "keep").writeText("original")
        File(privateDir, "m11-save-restore.properties").writeText("corrupt")
        assertFalse(SaveRestoreTransaction(privateDir).recover())
        assertEquals("original", File(live, "keep").readText())
    }

    @Test fun operationCenterSimultaneousFailuresAreReadOnly() {
        val cards = OperationCenterPolicy.build("ERROR", "REVIEW_REQUIRED", false, false,
            false, true, setOf("download", "mod_batch", "save_restore"), listOf("CONFLICT"))
        for (key in listOf("download", "mod_batch", "save_restore", "mod_review", "sync")) {
            assertEquals(CenterStatus.ACTION_REQUIRED, cards.single { it.id == key }.status)
        }
        assertEquals(cards.size, cards.map { it.id }.toSet().size)
    }

    @Test fun capacityCheckNeverGuessesUnknownDownloadSize() {
        val budget = StoragePlanner.downloadPlan(root, null)
        assertNull(budget.payloadBytes)
        assertNull(budget.requiredBytes)
        // Unknown payload must never be reported sufficient. A conservative
        // false is valid when the filesystem itself cannot be probed.
        assertFalse(budget.sufficient == true)
    }
}
