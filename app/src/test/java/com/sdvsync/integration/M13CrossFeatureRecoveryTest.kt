package com.sdvsync.integration

import com.sdvsync.diagnostics.CenterStatus
import com.sdvsync.diagnostics.OperationCenterPolicy
import com.sdvsync.download.GameDownloadRecovery
import com.sdvsync.mods.ModBatchTransaction
import com.sdvsync.mods.ModProfileTransaction
import com.sdvsync.mods.ProfileFolderMove
import com.sdvsync.saves.SaveRestoreTransaction
import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

/** Integrate independent M6, M8, M9, M11 and M12 producers on one private-root fixture. */
class M13CrossFeatureRecoveryTest {
    private fun inFixture(run: (File, File) -> Unit) {
        val root = Files.createTempDirectory("m13-cross-").toFile()
        val privateDir = File(root, "private").apply { mkdirs() }
        try { run(root, privateDir) } finally { root.deleteRecursively() }
    }

    @Test fun gameCheckpointSurvivesUnrelatedModProfileRollback() = inFixture { root, privateDir ->
        val game = File(root, "game").apply { mkdirs() }
        val mods = File(root, "Mods").apply { mkdirs() }
        val alpha = File(mods, "alpha").apply { mkdirs() }
        File(alpha, "manifest.json").writeText("original")
        val download = GameDownloadRecovery(privateDir)
        download.beginNew(game, "public", "windows", true)
        val profile = ModProfileTransaction(privateDir, mods)
        profile.prepare(listOf(ProfileFolderMove("alpha", ".alpha")))
        assertTrue(alpha.renameTo(File(mods, ".alpha")))
        assertTrue(profile.recover())
        assertEquals("original", File(alpha, "manifest.json").readText())
        download.requireMatching(game, "public", "windows", true)
        assertNotNull(download.pending())
        download.discard()
        assertNull(download.pending())
    }

    @Test fun corruptBatchJournalCannotBeErasedBySuccessfulGameCompletion() = inFixture { root, privateDir ->
        val mods = File(root, "Mods").apply { mkdirs() }
        val game = File(root, "game").apply { mkdirs() }
        File(privateDir, "m9-mod-batch.properties").writeText("corrupted")
        val batch = ModBatchTransaction(privateDir, mods)
        assertFalse(batch.recover())
        val download = GameDownloadRecovery(privateDir)
        download.beginNew(game, "public", "windows", true)
        download.completed()
        assertNull(download.pending())
        assertTrue(File(privateDir, "m9-mod-batch.properties").isFile)
        assertFalse(batch.recover())
    }

    @Test fun corruptSaveJournalBlocksSaveRecoveryWithoutTouchingOtherCheckpoints() = inFixture { root, privateDir ->
        val game = File(root, "game").apply { mkdirs() }
        val download = GameDownloadRecovery(privateDir)
        download.beginNew(game, "public", "linux", false)
        File(privateDir, "m11-save-restore.properties").writeText("invalid")
        assertFalse(SaveRestoreTransaction(privateDir).recover())
        download.requireMatching(game, "public", "linux", false)
        assertTrue(File(privateDir, "m11-save-restore.properties").exists())
    }

    @Test fun operationCenterShowsConcurrentFailuresWithoutInvokingRecovery() {
        val cards = OperationCenterPolicy.build(
            "ERROR", "REVIEW_REQUIRED", false, false, false, true,
            setOf("download", "mod_batch", "save_restore"), listOf("CONFLICT"))
        for (id in listOf("download", "mod_batch", "save_restore", "mod_review", "sync")) {
            assertEquals(CenterStatus.ACTION_REQUIRED, cards.single { it.id == id }.status)
        }
        assertEquals(cards.size, cards.map { it.id }.toSet().size)
    }

    @Test fun unknownJournalIdentifierNeverBecomesAnOperation() {
        val cards = OperationCenterPolicy.build("IDLE", "IDLE", false, false, false, false,
            setOf("../secret", "m11-save-restore.properties", "fake"), listOf("secret"))
        assertEquals(listOf("game_download", "mod_download"), cards.map { it.id })
    }
}
