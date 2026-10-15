package com.sdvsync.saves

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class SaveRestoreTransactionTest {
    private fun fixture(block: (File, File, File, SaveRestoreTransaction) -> Unit) {
        val dir = Files.createTempDirectory("m11-save-").toFile()
        val backup = File(dir, "backup").apply { mkdir() }
        val target = File(dir, "save").apply { mkdir() }
        val privateDir = File(dir, "private").apply { mkdir() }
        try { block(dir, backup, target, SaveRestoreTransaction(privateDir)) }
        finally { dir.deleteRecursively() }
    }
    @Test fun restoreReplacesFilesButPreservesExtraFiles() = fixture { _, backup, target, tx ->
        File(backup, "SaveGameInfo").writeText("old")
        File(target, "SaveGameInfo").writeText("new")
        File(target, "user_config").writeText("keep")
        assertTrue(tx.restore(backup, target))
        assertEquals("old", File(target, "SaveGameInfo").readText())
        assertEquals("keep", File(target, "user_config").readText())
        assertTrue(tx.recover())
    }
    @Test fun unsafeBackupNeverTouchesTarget() = fixture { _, backup, target, tx ->
        File(target, "SaveGameInfo").writeText("live")
        val foreign = File(target.parentFile, "foreign").apply { writeText("data") }
        Files.createSymbolicLink(File(backup, "link").toPath(), foreign.toPath())
        assertTrue(runCatching { tx.restore(backup, target) }.isFailure)
        assertEquals("live", File(target, "SaveGameInfo").readText())
    }
    @Test fun noUnsafeReplacementOfDirectory() = fixture { _, backup, target, tx ->
        File(backup, "SaveGameInfo").writeText("old")
        File(target, "SaveGameInfo").mkdir()
        assertTrue(runCatching { tx.restore(backup, target) }.isFailure)
        assertTrue(File(target, "SaveGameInfo").isDirectory)
    }
    @Test fun recoveryRollsBackAfterFirstRename() = fixture { root, backup, target, tx ->
        File(target, "SaveGameInfo").writeText("original")
        val id = "00000000-0000-0000-0000-000000000001"
        val stage = File(root, ".m11-save-stage-$id").apply { mkdir(); File(this, "SaveGameInfo").writeText("replacement") }
        val hold = File(root, ".m11-save-hold-$id")
        val digest = fingerprintForTest(stage)
        writeJournal(root, target, stage, hold, digest, true)
        assertTrue(target.renameTo(hold))
        assertTrue(tx.recover())
        assertEquals("original", File(target, "SaveGameInfo").readText())
    }
    @Test fun recoveryRollsBackAfterActivation() = fixture { root, _, target, tx ->
        File(target, "SaveGameInfo").writeText("original")
        val id = "00000000-0000-0000-0000-000000000002"
        val stage = File(root, ".m11-save-stage-$id").apply { mkdir(); File(this, "SaveGameInfo").writeText("replacement") }
        val hold = File(root, ".m11-save-hold-$id")
        val digest = fingerprintForTest(stage)
        writeJournal(root, target, stage, hold, digest, true)
        assertTrue(target.renameTo(hold)); assertTrue(stage.renameTo(target))
        assertTrue(tx.recover())
        assertEquals("original", File(target, "SaveGameInfo").readText())
    }
    @Test fun tamperedOriginalHoldBlocksRecovery() = fixture { root, _, target, tx ->
        File(target, "SaveGameInfo").writeText("original")
        val id = "00000000-0000-0000-0000-000000000004"
        val stage = File(root, ".m11-save-stage-$id").apply {
            mkdir(); File(this, "SaveGameInfo").writeText("replacement")
        }
        val hold = File(root, ".m11-save-hold-$id")
        val digest = fingerprintForTest(stage)
        writeJournal(root, target, stage, hold, digest, true)
        assertTrue(target.renameTo(hold))
        File(hold, "SaveGameInfo").writeText("tampered")
        assertFalse(tx.recover())
        assertFalse(target.exists())
        assertTrue(File(root, "private/m11-save-restore.properties").exists())
    }
    @Test fun recoveryWithInjectedDataFailsClosed() = fixture { root, _, target, tx ->
        File(target, "SaveGameInfo").writeText("original")
        val id = "00000000-0000-0000-0000-000000000003"
        val stage = File(root, ".m11-save-stage-$id").apply { mkdir(); File(this, "SaveGameInfo").writeText("replacement") }
        val hold = File(root, ".m11-save-hold-$id")
        val digest = fingerprintForTest(stage)
        writeJournal(root, target, stage, hold, digest, true)
        File(stage, "injected").writeText("unexpected")
        assertFalse(tx.recover())
        assertEquals("original", File(target, "SaveGameInfo").readText())
        assertTrue(File(root, "private/m11-save-restore.properties").exists())
    }
    private fun fingerprintForTest(stage: File): String {
        val md = java.security.MessageDigest.getInstance("SHA-256")
        for (f in stage.listFiles()!!.sortedBy { it.name }) {
            md.update(f.name.toByteArray(Charsets.UTF_8));md.update(0.toByte())
            md.update(f.length().toString().toByteArray());md.update(0.toByte())
            md.update(f.readBytes())
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
    private fun writeJournal(root: File, target: File, stage: File, hold: File, hash: String, had: Boolean) {
        val p = java.util.Properties().apply {
            setProperty("schema", "1");setProperty("target", target.absolutePath)
            setProperty("stage", stage.absolutePath);setProperty("hold", hold.absolutePath)
            setProperty("fingerprint", hash)
            setProperty("original", if (had) fingerprintForTest(target) else "absent")
            setProperty("had_target", had.toString())
        }
        File(root, "private/m11-save-restore.properties").outputStream().use { p.store(it, "test") }
    }
}
