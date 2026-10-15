package com.sdvsync.mods

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class ModProfileTransactionTest {
    private fun fixture(): Triple<File, File, ModProfileTransaction> {
        val root = Files.createTempDirectory("m8-profile-test-").toFile()
        val mods = File(root, "Mods").also { check(it.mkdir()) }
        val privateDir = File(root, "private").also { check(it.mkdir()) }
        return Triple(root, mods, ModProfileTransaction(privateDir, mods))
    }
    private val moves = listOf(ProfileFolderMove("alpha", ".alpha"), ProfileFolderMove(".beta", "beta"))

    @Test fun journalBeforeAnyRenameRollsBackAndClears() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            tx.prepare(moves)
            assertTrue(ModProfileTransaction(File(root, "private"), mods).recover())
            assertTrue(File(mods, "alpha").isDirectory)
            assertTrue(File(mods, ".beta").isDirectory)
            assertFalse(File(root, "private/m8-profile-transaction.properties").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun deathBetweenTwoRenamesRollsBackExactly() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            tx.prepare(moves)
            assertTrue(File(mods, "alpha").renameTo(File(mods, ".alpha")))
            assertTrue(ModProfileTransaction(File(root, "private"), mods).recover())
            assertTrue(File(mods, "alpha").isDirectory)
            assertTrue(File(mods, ".beta").isDirectory)
            assertFalse(File(mods, ".alpha").exists())
            assertFalse(File(mods, "beta").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun deathAfterAllRenamesStillRollsBack() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            tx.prepare(moves)
            assertTrue(File(mods, "alpha").renameTo(File(mods, ".alpha")))
            assertTrue(File(mods, ".beta").renameTo(File(mods, "beta")))
            assertTrue(ModProfileTransaction(File(root, "private"), mods).recover())
            assertTrue(File(mods, "alpha").isDirectory)
            assertTrue(File(mods, ".beta").isDirectory)
        } finally { root.deleteRecursively() }
    }

    @Test fun collisionPreservesAllFoldersAndKeepsJournal() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            tx.prepare(moves)
            assertTrue(File(mods, ".alpha").mkdir())
            assertFalse(tx.recover())
            assertTrue(File(mods, "alpha").exists())
            assertTrue(File(mods, ".alpha").exists())
            assertTrue(File(root, "private/m8-profile-transaction.properties").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun successfulApplyLeavesNoJournal() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            assertEquals(2, tx.apply(moves))
            assertTrue(File(mods, ".alpha").isDirectory)
            assertTrue(File(mods, "beta").isDirectory)
            assertFalse(File(root, "private/m8-profile-transaction.properties").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun unsafeOrConflictingPlansRejectWithoutJournal() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            for (bad in listOf(
                listOf(ProfileFolderMove("../outside", ".outside")),
                listOf(ProfileFolderMove("alpha", ".beta")),
                listOf(ProfileFolderMove("alpha", "alpha")),
                listOf(ProfileFolderMove("alpha", ".alpha"), ProfileFolderMove(".beta", "alpha"))
            )) assertTrue(runCatching { tx.apply(bad) }.isFailure)
            assertFalse(File(root, "private/m8-profile-transaction.properties").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun symlinkAfterCrashIsFailClosed() {
        val (root, mods, tx) = fixture()
        try {
            File(mods, "alpha").mkdir(); File(mods, ".beta").mkdir()
            tx.prepare(moves)
            val destination = File(mods, ".alpha").toPath()
            Files.createSymbolicLink(destination, File(mods, "alpha").toPath())
            assertFalse(tx.recover())
            assertTrue(File(root, "private/m8-profile-transaction.properties").exists())
        } finally { root.deleteRecursively() }
    }
}
