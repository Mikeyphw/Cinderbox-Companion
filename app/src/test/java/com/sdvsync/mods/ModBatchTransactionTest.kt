package com.sdvsync.mods

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class ModBatchTransactionTest {
    private data class Fixture(val root: File, val mods: File, val privateDir: File,
                               val incoming: File, val tx: ModBatchTransaction) {
        fun entries(): List<BatchModEntry> = listOf(
            BatchModEntry("alpha", File(incoming, "alpha")),
            BatchModEntry("beta", File(incoming, "beta")),
            BatchModEntry("gamma", File(incoming, "gamma"))
        )
        fun newTransaction() = ModBatchTransaction(privateDir, mods)
        fun journal() = File(privateDir, "m9-mod-batch.properties")
        fun original(name: String) = File(mods, "$name/old.txt").readText()
    }
    private fun fixture(): Fixture {
        val root = Files.createTempDirectory("m9-batch-test-").toFile()
        val mods = File(root, "Mods").also { check(it.mkdir()) }
        val privateDir = File(root, "private").also { check(it.mkdir()) }
        val incoming = File(root, "download").also { check(it.mkdir()) }
        for (name in listOf("alpha", "beta")) {
            val folder = File(mods, name).also { check(it.mkdir()) }
            File(folder, "old.txt").writeText("old-$name")
            File(folder, "config.json").writeText("settings-$name")
        }
        for (name in listOf("alpha", "beta", "gamma")) {
            val folder = File(incoming, name).also { check(it.mkdir()) }
            File(folder, "manifest.json").writeText("{\"Name\":\"$name\"}")
            File(folder, "new.txt").writeText("new-$name")
        }
        return Fixture(root, mods, privateDir, incoming, ModBatchTransaction(privateDir, mods))
    }
    @Test fun successfulBatchCommitsAllWithoutJournal() {
        val f = fixture()
        try {
            val backedUp = mutableListOf<String>()
            assertEquals(3, f.tx.install(f.entries(), snapshot = { backedUp += it.name }))
            assertEquals(listOf("alpha", "beta"), backedUp)
            for (name in listOf("alpha", "beta", "gamma")) {
                assertEquals("new-$name", File(f.mods, "$name/new.txt").readText())
            }
            assertEquals("settings-alpha", File(f.mods, "alpha/config.json").readText())
            assertEquals("settings-beta", File(f.mods, "beta/config.json").readText())
            assertFalse(f.journal().exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun exceptionDuringSecondModRollsBackAll() {
        val f = fixture()
        try {
            assertTrue(runCatching {
                f.tx.install(f.entries(), snapshot = {}, afterStep = { if (it == 1) error("simulated failure") })
            }.isFailure)
            assertEquals("old-alpha", f.original("alpha"))
            assertEquals("old-beta", f.original("beta"))
            assertFalse(File(f.mods, "gamma").exists())
            assertFalse(f.journal().exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun processDeathAfterFirstModRecoversAll() {
        val f = fixture()
        try {
            assertTrue(runCatching {
                f.tx.install(f.entries(), snapshot = {}, afterStep = { if (it == 0) throw AssertionError("kill") })
            }.isFailure)
            assertTrue(f.journal().exists())
            assertTrue(f.newTransaction().recover())
            assertEquals("old-alpha", f.original("alpha"))
            assertEquals("old-beta", f.original("beta"))
            assertFalse(File(f.mods, "gamma").exists())
            assertFalse(f.journal().exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun processDeathAfterAllRenamesStillRecoversOriginals() {
        val f = fixture()
        try {
            assertTrue(runCatching {
                f.tx.install(f.entries(), snapshot = {}, afterStep = { if (it == 2) throw AssertionError("kill") })
            }.isFailure)
            assertTrue(f.newTransaction().recover())
            assertEquals("old-alpha", f.original("alpha"))
            assertEquals("old-beta", f.original("beta"))
            assertFalse(File(f.mods, "gamma").exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun collisionAfterDeathBlocksWholeRecovery() {
        val f = fixture()
        try {
            runCatching { f.tx.install(f.entries(), snapshot = {}, afterStep = { if (it == 0) throw AssertionError() }) }
            File(f.mods, "gamma").also { check(it.mkdir()); File(it, "outside.txt").writeText("unrelated") }
            assertFalse(f.newTransaction().recover())
            assertTrue(f.journal().exists())
            assertEquals("new-alpha", File(f.mods, "alpha/new.txt").readText())
            assertEquals("unrelated", File(f.mods, "gamma/outside.txt").readText())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun editedPublishedModBlocksRecoveryWithoutDeleting() {
        val f = fixture()
        try {
            runCatching { f.tx.install(f.entries(), snapshot = {}, afterStep = { if (it == 0) throw AssertionError() }) }
            File(f.mods, "alpha/user-config.json").writeText("my settings")
            assertFalse(f.newTransaction().recover())
            assertTrue(f.journal().exists())
            assertTrue(File(f.mods, "alpha/user-config.json").exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun symlinkAfterCrashBlocksRecovery() {
        val f = fixture()
        try {
            runCatching { f.tx.install(f.entries(), snapshot = {}, afterStep = { if (it == 0) throw AssertionError() }) }
            Files.createSymbolicLink(File(f.mods, "gamma").toPath(), File(f.mods, "alpha").toPath())
            assertFalse(f.newTransaction().recover())
            assertTrue(f.journal().exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun invalidInputsFailBeforeTouchingExistingMods() {
        val f = fixture()
        try {
            val bad = listOf(
                listOf(BatchModEntry("../outside", File(f.incoming, "alpha"))),
                listOf(BatchModEntry("alpha", File(f.incoming, "alpha")),
                    BatchModEntry("alpha", File(f.incoming, "beta"))),
                listOf(BatchModEntry(".m9-batch-trap", File(f.incoming, "alpha")))
            )
            for (plan in bad) assertTrue(runCatching { f.tx.install(plan, snapshot = {}) }.isFailure)
            assertEquals("old-alpha", f.original("alpha"))
            assertEquals("old-beta", f.original("beta"))
            assertFalse(f.journal().exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun staleApprovalRejectsBatchBeforeModification() {
        val f = fixture()
        try {
            val expected = f.tx.destinationFingerprint(listOf("alpha", "beta", "gamma"))
            File(f.mods, "alpha/old.txt").writeText("changed")
            assertTrue(runCatching {
                f.tx.install(f.entries(), snapshot = {}, expectedExistingDigest = expected)
            }.isFailure)
            assertEquals("changed", f.original("alpha"))
            assertFalse(f.journal().exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun fingerprintRejectsChangedContentsEvenWithSameFileCount() {
        val f = fixture()
        try {
            val before = f.tx.destinationFingerprint(listOf("alpha", "beta", "gamma"))
            File(f.mods, "alpha/old.txt").writeText("different-value")
            assertNotEquals(before, f.tx.destinationFingerprint(listOf("alpha", "beta", "gamma")))
            assertEquals(f.tx.destinationFingerprint(listOf("alpha", "beta", "gamma")),
                f.tx.destinationFingerprint(listOf("gamma", "beta", "alpha")))
        } finally { f.root.deleteRecursively() }
    }
}
