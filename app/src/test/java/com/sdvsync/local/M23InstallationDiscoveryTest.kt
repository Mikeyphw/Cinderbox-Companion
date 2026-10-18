package com.sdvsync.local

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

/** Synthetic private temporary roots. No production storage, Steam or Android device. */
class M23InstallationDiscoveryTest {
    private fun withRoot(test: (File) -> Unit) {
        val root = Files.createTempDirectory("m23-private-").toFile()
        try { test(root) } finally { root.deleteRecursively() }
    }

    private fun game(dir: File) {
        assertTrue(dir.mkdirs() || dir.isDirectory)
        listOf("Stardew Valley.dll", "StardewValley.GameData.dll", "BmFont.dll",
            "xTile.dll", "Lidgren.Network.dll").forEach { File(dir, it).writeText("synthetic") }
        File(dir, "Content").mkdir()
        File(dir, "Content/asset.xnb").writeText("synthetic")
    }

    @Test fun completeLookingBytesRemainUnverified() = withRoot { root ->
        val install = File(root, "desktop/GameFiles")
        game(install)
        val report = M23InstallationDiscovery.inspect(File(root,"unselected"),root)
        assertEquals(M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED,report.modern.status)
        assertFalse(report.modern.verified)
        assertFalse(report.modern.canInstallOrOverwrite)
        assertEquals("UNKNOWN_NO_AUTHENTICATED_MANIFEST",report.modern.version)
        assertFalse(report.downloadAllowed)
        assertTrue(report.gameAlreadyPresent)
    }

    @Test fun legacyAndModernConflictsNeverTriggerMigration() = withRoot { root ->
        game(File(root, "GameFiles"))
        game(File(root, "desktop/GameFiles"))
        val before = File(root, "GameFiles/Stardew Valley.dll").readBytes()
        val report = M23InstallationDiscovery.inspect(root,root)
        assertTrue(report.layoutConflict)
        assertTrue(before.contentEquals(File(root,"GameFiles/Stardew Valley.dll").readBytes()))
        assertFalse(report.writesPerformed)
    }

    @Test fun partialGameAndStagedArchiveAreNotInstallation() = withRoot { root ->
        val partial = File(root,"desktop/GameFiles"); partial.mkdirs()
        File(partial,"stardew.zip").writeText("untrusted")
        val report = M23InstallationDiscovery.inspect(File(root,"missing"),root)
        assertEquals(M23InstallationDiscovery.Status.PARTIAL,report.modern.status)
        assertTrue(report.modern.evidence.contains(M23InstallationDiscovery.Evidence.UNTRUSTED_ARCHIVE))
        assertNull(report.modern.observedBytes)
    }

    @Test fun unknownOwnershipCheckpointRequiresReview() = withRoot { root ->
        game(File(root,"desktop/GameFiles"))
        File(root,"desktop/GameFiles/.cinderbox-download.session").writeText("unowned")
        assertEquals(M23InstallationDiscovery.Status.RECOVERY_REVIEW,
            M23InstallationDiscovery.inspect(root,root).modern.status)
    }

    @Test fun symlinksAreNotFollowed() = withRoot { root ->
        val outside = File(root,"outside");game(outside)
        val linked = File(root,"desktop/GameFiles");linked.parentFile.mkdirs()
        Files.createSymbolicLink(linked.toPath(),outside.toPath())
        assertEquals(M23InstallationDiscovery.Status.UNSAFE_LINK,
            M23InstallationDiscovery.inspect(linked,root).modern.status)
    }

    @Test fun unreadableScaleBoundIsExplicit() = withRoot { root ->
        val many = File(root,"desktop/GameFiles");many.mkdirs()
        repeat(M23InstallationDiscovery.MAX_CHILDREN + 1) { File(many, "f$it").writeText("a") }
        assertEquals(M23InstallationDiscovery.Status.INACCESSIBLE,
            M23InstallationDiscovery.inspect(many,root).modern.status)
    }

    @Test fun interruptedSmapiRemainsDistinctFromDetected() = withRoot { root ->
        val smapi = File(root,"smapi-internal"); smapi.mkdir()
        File(smapi,"SMAPI.dll").writeText("synthetic")
        assertEquals(M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED,
            M23InstallationDiscovery.inspect(root,root).smapi.status)
        File(root,".smapi-internal.sdvsync-backup").mkdir()
        assertEquals(M23InstallationDiscovery.Status.RECOVERY_REVIEW,
            M23InstallationDiscovery.inspect(root,root).smapi.status)
    }

    @Test fun readOnlyScannerDoesNotCreatePermissionProbe() = withRoot { root ->
        val selected = File(root,"selected")
        val before = root.walkTopDown().map { it.relativeTo(root).path }.toSet()
        val report = InstallationScanner.scan(selected,false,root)
        val after = root.walkTopDown().map { it.relativeTo(root).path }.toSet()
        assertEquals(before,after)
        assertFalse(report.storage.writable)
        assertNotNull(report.discovery)
        assertFalse(report.discovery!!.writesPerformed)
        assertEquals(InstallHealth.INACCESSIBLE,
            InstallationScanner.scan(selected,false,root,false).cinderboxApp.health)
    }
}
