package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import org.junit.Assert.*
import org.junit.Test

class SmapiTransactionalInstallerTest {
    private fun zip(root: File, vararg entries: Pair<String, String>): File {
        val archive = File(root, "archive.zip")
        ZipOutputStream(archive.outputStream()).use { out ->
            for ((name, body) in entries) {
                out.putNextEntry(ZipEntry(name))
                out.write(body.toByteArray())
                out.closeEntry()
            }
        }
        return archive
    }

    @Test fun validArchiveAtomicallyReplacesOldTree() {
        val root = Files.createTempDirectory("smapi-test").toFile()
        try {
            val target = File(root, "smapi-internal").apply { mkdir() }
            File(target, "old.txt").writeText("old")
            val archive = zip(root, "new/file.txt" to "new")
            val files = SmapiTransactionalInstaller.install(archive, target)
            assertEquals(1, files)
            assertEquals("new", File(target, "new/file.txt").readText())
            assertFalse(File(target, "old.txt").exists())
            assertFalse(File(root, ".smapi-internal.sdvsync-backup").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun rejectedArchiveNeverTouchesExistingInstallation() {
        val root = Files.createTempDirectory("smapi-reject").toFile()
        try {
            val target = File(root, "smapi-internal").apply { mkdir() }
            File(target, "keep.txt").writeText("safe")
            val archive = zip(root, "../outside.txt" to "evil")
            try {
                SmapiTransactionalInstaller.install(archive, target)
                fail("Traversal must fail")
            } catch (_: IllegalArgumentException) { }
            assertEquals("safe", File(target, "keep.txt").readText())
            assertFalse(File(root, "outside.txt").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun recoverRestoresOldTreeAfterCrashBeforePromotion() {
        val root = Files.createTempDirectory("smapi-recover").toFile()
        try {
            val target = File(root, "smapi-internal")
            val backup = File(root, ".smapi-internal.sdvsync-backup").apply { mkdir() }
            File(backup, "old.txt").writeText("restored")
            SmapiTransactionalInstaller.recover(target)
            assertEquals("restored", File(target, "old.txt").readText())
            assertFalse(backup.exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun duplicateEntriesAreRejectedAndOriginalSurvives() {
        val root = Files.createTempDirectory("smapi-duplicate").toFile()
        try {
            val target = File(root, "smapi-internal").apply { mkdir() }
            File(target, "keep.txt").writeText("safe")
            val archive = zip(root, "Case.txt" to "a", "case.txt" to "b")
            try {
                SmapiTransactionalInstaller.install(archive, target)
                fail("Duplicate entry must fail")
            } catch (_: IllegalArgumentException) { }
            assertEquals("safe", File(target, "keep.txt").readText())
        } finally { root.deleteRecursively() }
    }
}
