package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class GameDownloadRecoveryTest {
    private fun inTemp(block: (File, File, GameDownloadRecovery) -> Unit) {
        val work = Files.createTempDirectory("m6-recovery-").toFile()
        val privateDir = File(work, "private").apply { mkdirs() }
        val destination = File(work, "game").apply { mkdirs() }
        try { block(privateDir, destination, GameDownloadRecovery(privateDir)) }
        finally { work.deleteRecursively() }
    }

    @Test fun interruptedSessionSurvivesReopening() = inTemp { root, dir, recovery ->
        recovery.beginNew(dir, "public", "windows", true)
        File(dir, "partial.bin").writeText("incomplete")
        val reopened = GameDownloadRecovery(root)
        assertNotNull(reopened.pending())
        reopened.requireMatching(dir, "public", "windows", true)
        assertTrue(File(dir, "partial.bin").isFile)
        reopened.completed()
        assertNull(reopened.pending())
    }

    @Test fun differentBranchAndDestinationCannotResume() = inTemp { _, dir, recovery ->
        recovery.beginNew(dir, "beta", "windows", true)
        assertThrows(IllegalStateException::class.java) {
            recovery.requireMatching(dir, "public", "windows", true)
        }
        assertThrows(IllegalStateException::class.java) {
            recovery.requireMatching(File(dir.parentFile, "other"), "beta", "windows", true)
        }
        assertThrows(IllegalStateException::class.java) {
            recovery.beginNew(dir, "public", "windows", true)
        }
    }

    @Test fun corruptMetadataFailsClosed() = inTemp { root, _, recovery ->
        File(root, "m6-game-download.properties").writeText("schema=wrong\n")
        assertThrows(IllegalStateException::class.java) { recovery.pending() }
    }

    @Test fun symlinkDestinationRejected() = inTemp { _, dir, recovery ->
        val link = File(dir.parentFile, "linked")
        Files.createSymbolicLink(link.toPath(), dir.toPath())
        assertThrows(IllegalArgumentException::class.java) {
            recovery.beginNew(link, "public", "windows", true)
        }
    }

    @Test fun missingOrChangedOwnershipMarkerNeverResumes() = inTemp { _, dir, recovery ->
        recovery.beginNew(dir, "public", "windows", true)
        val marker = File(dir, ".cinderbox-download.session")
        marker.writeText("unrelated")
        assertThrows(IllegalStateException::class.java) {
            recovery.requireMatching(dir, "public", "windows", true)
        }
        // Discard cannot delete a marker it does not own.
        recovery.discard()
        assertEquals("unrelated", marker.readText())
        assertNull(recovery.pending())
    }

    @Test fun discardKeepsDownloadedFiles() = inTemp { _, dir, recovery ->
        recovery.beginNew(dir, "public", "windows", false)
        File(dir, "incomplete").writeText("keep")
        recovery.discard()
        assertNull(recovery.pending())
        assertEquals("keep", File(dir, "incomplete").readText())
    }

    @Test fun integrityLedgerDetectsChangesAndMissingFiles() = inTemp { root, dir, _ ->
        val game = File(dir, "Content").apply { mkdirs() }
        File(game, "a.bin").writeText("hello")
        File(game, "b.bin").writeText("world")
        val integrity = GameFileIntegrity(root)
        assertTrue(integrity.verifyAndRecord(dir).passed)
        assertTrue(integrity.verifyRecorded(dir).passed)
        File(game, "a.bin").writeText("HELLO")
        assertFalse(integrity.verifyRecorded(dir).passed)
        File(game, "a.bin").writeText("hello")
        assertTrue(File(game, "b.bin").delete())
        assertFalse(integrity.verifyRecorded(dir).passed)
    }

    @Test fun integrityRejectsExtraFileAndSymlink() = inTemp { root, dir, _ ->
        File(dir, "game.bin").writeText("known")
        val integrity = GameFileIntegrity(root)
        assertTrue(integrity.verifyAndRecord(dir).passed)
        File(dir, "unexpected.txt").writeText("new")
        assertFalse(integrity.verifyRecorded(dir).passed)
        val link = File(dir, "linked")
        Files.createSymbolicLink(link.toPath(), File(dir, "game.bin").toPath())
        assertThrows(IllegalArgumentException::class.java) { integrity.verifyRecorded(dir) }
    }
}
