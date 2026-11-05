package com.sdvsync.mods

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

/** No live Mods directory, shell, Android device or game data: every test creates temp roots. */
class ModBulkTransactionTest {
    private data class Fixture(val root: File, val mods: File, val privateRoot: File) {
        fun manager() = ModBulkTransaction(privateRoot, mods)
        fun folder(name: String, content: String = name): File = File(mods, name).also {
            check(it.mkdir()); File(it, "manifest.json").writeText("{\"name\":\"$content\"}")
            check(File(it, "nested").mkdir())
            File(it, "nested/config.json").writeBytes(byteArrayOf(0, 1, 2, 3, 4, 127))
        }
        fun bytes(name: String): List<ByteArray> = listOf(
            File(mods, "$name/manifest.json").readBytes(),
            File(mods, "$name/nested/config.json").readBytes())
        fun clean() = root.deleteRecursively()
    }
    private fun fixture(): Fixture {
        val root = Files.createTempDirectory("m25-bulk-fixture-").toFile()
        val mods = File(root, "Mods").also { check(it.mkdir()) }
        val privateRoot = File(root, "private").also { check(it.mkdir()) }
        return Fixture(root, mods, privateRoot)
    }
    private val fingerprint = "c".repeat(64)
    private val moves = listOf(ProfileFolderMove("alpha", ".alpha"),
        ProfileFolderMove(".beta", "beta"))
    private fun assertBytes(a: List<ByteArray>, b: List<ByteArray>) {
        a.zip(b).forEach { (x, y) -> assertArrayEquals(x, y) }
    }

    @Test fun fullyAppliedChangesBothAndPreservesEveryFileByte() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val a = f.bytes("alpha"); val b = f.bytes(".beta")
            val tx = f.manager()
            val review = tx.review(moves, fingerprint)
            assertEquals(2, tx.apply(review, fingerprint))
            assertFalse(File(f.mods, "alpha").exists())
            assertFalse(File(f.mods, ".beta").exists())
            assertBytes(a, f.bytes(".alpha")); assertBytes(b, f.bytes("beta"))
            assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
            assertTrue(runCatching { tx.apply(review, fingerprint) }.isFailure)
        } finally { f.clean() }
    }

    @Test fun staleMetadataAndChangedBytesAreRefusedBeforeJournal() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val tx = f.manager()
            val review = tx.review(moves, fingerprint)
            assertTrue(runCatching { tx.apply(review, "d".repeat(64)) }.isFailure)
            File(f.mods, "alpha/nested/config.json").appendText("changed")
            assertTrue(runCatching { tx.apply(review, fingerprint) }.isFailure)
            assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
            assertTrue(File(f.mods, "alpha").isDirectory)
            assertTrue(File(f.mods, ".beta").isDirectory)
        } finally { f.clean() }
    }

    @Test fun directChildInventoryDriftInvalidatesReview() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val tx = f.manager(); val review = tx.review(moves, fingerprint)
            f.folder("unrelated")
            assertTrue(runCatching { tx.apply(review, fingerprint) }.isFailure)
            assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
        } finally { f.clean() }
    }

    @Test fun zeroAndTooManyAndConflictingPlansAreRejected() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val tx = f.manager()
            assertTrue(runCatching { tx.review(emptyList(), fingerprint) }.isFailure)
            assertTrue(runCatching { tx.review(List(513) { ProfileFolderMove("alpha", ".alpha") }, fingerprint) }.isFailure)
            assertTrue(runCatching { tx.review(listOf(ProfileFolderMove("alpha", ".alpha"),
                ProfileFolderMove("alpha", ".alpha")), fingerprint) }.isFailure)
            assertTrue(runCatching { tx.review(listOf(ProfileFolderMove("alpha", ".beta")), fingerprint) }.isFailure)
            assertTrue(runCatching { tx.review(listOf(ProfileFolderMove("../alpha", ".alpha")), fingerprint) }.isFailure)
            assertTrue(runCatching { tx.review(listOf(ProfileFolderMove("alpha", "alpha")), fingerprint) }.isFailure)
            assertTrue(runCatching { tx.review(listOf(ProfileFolderMove("alpha", "/absolute")), fingerprint) }.isFailure)
            assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
        } finally { f.clean() }
    }

    @Test fun all512MovesCanBePreflightedWithoutChangingFolders() {
        val f = fixture()
        try {
            val many = (0 until 512).map { i ->
                f.folder("mod$i"); ProfileFolderMove("mod$i", ".mod$i") }
            val review = f.manager().review(many, fingerprint)
            assertEquals(512, review.moves.size)
            assertEquals(512, review.sourceHashes.size)
            assertFalse(File(f.mods, ".mod511").exists())
        } finally { f.clean() }
    }

    @Test fun processDeathAfterJournalAndAfterEachRenameRestoresExactBytes() {
        for (completed in 0..2) {
            val f = fixture()
            try {
                f.folder("alpha"); f.folder(".beta")
                val a = f.bytes("alpha"); val b = f.bytes(".beta")
                val tx = f.manager()
                tx.prepare(tx.review(moves, fingerprint))
                for (move in moves.take(completed)) {
                    assertTrue(File(f.mods, move.from).renameTo(File(f.mods, move.to)))
                }
                assertTrue(f.manager().recover())
                assertBytes(a, f.bytes("alpha")); assertBytes(b, f.bytes(".beta"))
                assertFalse(File(f.mods, ".alpha").exists())
                assertFalse(File(f.mods, "beta").exists())
                assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
                assertTrue(f.manager().recover())
            } finally { f.clean() }
        }
    }

    @Test fun collisionAfterPartialMoveRetainsJournalAndNeverClaimsSuccess() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val tx = f.manager()
            tx.prepare(tx.review(moves, fingerprint))
            assertTrue(File(f.mods, "alpha").renameTo(File(f.mods, ".alpha")))
            f.folder("alpha", "unexpected")
            assertFalse(f.manager().recover())
            assertTrue(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
            assertTrue(File(f.mods, ".beta").exists())
            assertTrue(runCatching { f.manager().review(moves, fingerprint) }.isFailure)
        } finally { f.clean() }
    }

    @Test fun modifiedMovedFolderStopsRecoveryAndPreservesJournal() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val tx = f.manager()
            tx.prepare(tx.review(moves, fingerprint))
            assertTrue(File(f.mods, "alpha").renameTo(File(f.mods, ".alpha")))
            File(f.mods, ".alpha/manifest.json").writeText("tampered")
            assertFalse(f.manager().recover())
            assertTrue(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
            assertFalse(File(f.mods, "alpha").exists())
        } finally { f.clean() }
    }

    @Test fun symlinkChildAndNestedSymlinkAreRejected() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val outside = File(f.root, "outside").also { it.writeText("private") }
            Files.createSymbolicLink(File(f.mods, "alpha/nested/link").toPath(), outside.toPath())
            assertTrue(runCatching { f.manager().review(moves, fingerprint) }.isFailure)
            Files.delete(File(f.mods, "alpha/nested/link").toPath())
            Files.createSymbolicLink(File(f.mods, ".alpha").toPath(), outside.toPath())
            assertTrue(runCatching { f.manager().review(moves, fingerprint) }.isFailure)
        } finally { f.clean() }
    }

    @Test fun rootSymlinkAndHardlinkRejectWithoutMutation() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val alias = File(f.root, "ModsAlias")
            Files.createSymbolicLink(alias.toPath(), f.mods.toPath())
            assertTrue(runCatching { ModBulkTransaction(f.privateRoot, alias).review(moves, fingerprint) }.isFailure)
            val file = File(f.mods, "alpha/manifest.json")
            val hardlink = File(f.mods, "alpha/manifest-copy.json")
            val linked = runCatching { Files.createLink(hardlink.toPath(), file.toPath()); true }.getOrElse { false }
            if (linked && runCatching { Files.getAttribute(file.toPath(), "unix:nlink") }.isSuccess) {
                assertTrue(runCatching { f.manager().review(moves, fingerprint) }.isFailure)
            }
            assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
        } finally { f.clean() }
    }

    @Test fun fileRenameAndDeletionBetweenReviewAndApplyAreRefused() {
        val f = fixture()
        try {
            f.folder("alpha"); f.folder(".beta")
            val tx = f.manager(); val review = tx.review(moves, fingerprint)
            File(f.mods, "alpha/manifest.json").delete()
            assertTrue(runCatching { tx.apply(review, fingerprint) }.isFailure)
            assertFalse(File(f.privateRoot, "m25-bulk-transaction.properties").exists())
        } finally { f.clean() }
    }
}
