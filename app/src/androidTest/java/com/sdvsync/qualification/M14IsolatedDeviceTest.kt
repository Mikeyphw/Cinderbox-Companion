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
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir
        root = Files.createTempDirectory(cache.toPath(), "m14-device-").toFile()
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
        assertThrows(IllegalStateException::class.java) {
            tx.install(listOf(BatchModEntry("alpha", first), BatchModEntry("beta", second)),
                snapshot = {}, afterStep = { i -> if (i == 0) error("M14 simulated interruption") })
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
        assertNull(budget.sufficient)
    }
}
