package com.sdvsync.local

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Test

class InstallationScannerTest {
    private fun game(root: File) {
        listOf("Stardew Valley.dll", "StardewValley.GameData.dll", "BmFont.dll",
            "xTile.dll", "Lidgren.Network.dll").forEach { File(root, it).writeText("test") }
        File(root, "Content").mkdir()
        File(root, "Content/asset.xnb").writeText("test")
    }

    @Test fun missingAndIncompleteAreDistinct() {
        val root = Files.createTempDirectory("m4-health").toFile()
        try {
            assertEquals(InstallHealth.MISSING, InstallationScanner.game(File(root, "no-game")).health)
            File(root, "broken").mkdir()
            File(root, "broken/partial").writeText("something")
            assertEquals(InstallHealth.INCOMPLETE, InstallationScanner.game(File(root, "broken")).health)
        } finally { root.deleteRecursively() }
    }

    @Test fun validStructureDoesNotClaimHashes() {
        val root = Files.createTempDirectory("m4-game").toFile()
        try {
            game(root)
            val report = InstallationScanner.game(root)
            assertEquals(InstallHealth.STRUCTURALLY_VALID, report.health)
            assertTrue(report.details.contains("not performed"))
            File(root, "BmFont.dll").delete()
            assertEquals(InstallHealth.INCOMPLETE, InstallationScanner.game(root).health)
        } finally { root.deleteRecursively() }
    }

    @Test fun symlinkNeverQualifiesAsWritableGame() {
        val root = Files.createTempDirectory("m4-link").toFile()
        try {
            game(root)
            val link = File(root.parentFile, "m4-link-${root.name}")
            try {
                Files.createSymbolicLink(link.toPath(), root.toPath())
                assertEquals(InstallHealth.INACCESSIBLE, InstallationScanner.game(link).health)
                assertFalse(StoragePreflight.check(link).writable)
            } finally { link.delete() }
        } finally { root.deleteRecursively() }
    }

    @Test fun storageProbeIsNonDestructive() {
        val root = Files.createTempDirectory("m4-storage").toFile()
        try {
            val before = root.list()?.toSet()
            assertTrue(StoragePreflight.check(root).writable)
            assertEquals(before, root.list()?.toSet())
            assertTrue(StoragePreflight.check(File(root, "new-game")).writable)
            assertFalse(File(root, "new-game").exists())
        } finally { root.deleteRecursively() }
    }

    @Test fun partialSmapiRequiresReview() {
        val root = Files.createTempDirectory("m4-smapi").toFile()
        try {
            assertEquals(InstallHealth.INCOMPLETE, InstallationScanner.smapi(root).health)
            File(root, "SMAPI.dll").writeText("example")
            assertEquals(InstallHealth.DETECTED, InstallationScanner.smapi(root).health)
            File(root.parentFile, ".${root.name}.sdvsync-backup").mkdir()
            try { assertEquals(InstallHealth.INCOMPLETE, InstallationScanner.smapi(root).health) }
            finally { File(root.parentFile, ".${root.name}.sdvsync-backup").delete() }
        } finally { root.deleteRecursively() }
    }
}
