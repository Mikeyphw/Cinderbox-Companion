package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

/** Only isolated host temporary trees, never an installed Cinderbox game. */
class M24StagedGameTransactionTest {
    private fun fixture(run: (File, File, GameDownloadRecovery) -> Unit) {
        val root = Files.createTempDirectory("m24-stage-").toFile()
        val privateDir = File(root, "private").apply { mkdir() }
        val finalDir = File(root, "game") // must initially be absent
        try { run(root, finalDir, GameDownloadRecovery(privateDir)) }
        finally { root.deleteRecursively() }
    }
    @Test fun liveTransferOnlyWritesToOwnedStage() = fixture { _, destination, rec ->
        rec.beginStaged(destination, "public", "windows", true)
        rec.bindSteamBuildId(121L)
        val stage = rec.requireActiveStage(destination)
        assertFalse(destination.exists())
        assertEquals(destination.parentFile, stage.parentFile)
        File(stage, "game.bin").writeText("stage-only")
        assertFalse(File(destination, "game.bin").exists())
        val restart = GameDownloadRecovery(stage.parentFile.resolve("private"))
        restart.requireSteamBuildId(121L)
        assertEquals(stage.canonicalFile, restart.requireActiveStage(destination))
    }
    @Test fun preexistingEmptyTargetCannotBeReplaced() = fixture { _, destination, rec ->
        destination.mkdir()
        assertThrows(IllegalStateException::class.java) {
            rec.beginStaged(destination, "public", "windows", true)
        }
        assertTrue(destination.isDirectory)
    }
    @Test fun promotionIsAtomicAndRecoversAcrossRestart() = fixture { _, destination, rec ->
        rec.beginStaged(destination, "public", "windows", true)
        rec.bindSteamBuildId(111L)
        File(rec.requireActiveStage(destination), "payload.bin").writeText("synthetic")
        rec.promoteStaged(destination)
        assertTrue(destination.resolve("payload.bin").isFile)
        assertTrue(rec.isPromotedStage(destination))
        assertThrows(IllegalStateException::class.java) { rec.requireActiveStage(destination) }
        val newOwner = GameDownloadRecovery(destination.parentFile.resolve("private"))
        assertTrue(newOwner.isPromotedStage(destination))
        newOwner.completed()
        assertNull(newOwner.pending())
        assertTrue(destination.resolve("payload.bin").isFile)
        assertFalse(destination.resolve(".cinderbox-download.session").exists())
    }
    @Test fun discardDoesNotEraseInterruptedStageBytes() = fixture { _, destination, rec ->
        rec.beginStaged(destination, "public", "windows", true)
        rec.bindSteamBuildId(111L)
        val stage = rec.requireActiveStage(destination)
        stage.resolve("partial.bin").writeText("retain")
        rec.discard()
        assertNull(rec.pending())
        assertEquals("retain", stage.resolve("partial.bin").readText())
        assertFalse(destination.exists())
    }
    @Test fun mismatchedBuildAndForgedOwnerFailClosed() = fixture { _, destination, rec ->
        rec.beginStaged(destination, "public", "windows", true)
        rec.bindSteamBuildId(111L)
        val stage = rec.requireActiveStage(destination)
        stage.resolve("partial.bin").writeText("retain")
        assertThrows(IllegalStateException::class.java) { rec.requireSteamBuildId(112L) }
        stage.resolve(".cinderbox-download.session").writeText("forged")
        assertThrows(IllegalStateException::class.java) { rec.promoteStaged(destination) }
        assertEquals("retain", stage.resolve("partial.bin").readText())
        assertFalse(destination.exists())
    }
}
