package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.local.InstallationScanner
import com.sdvsync.local.M23InstallationDiscovery
import java.io.File
import java.nio.file.Files
import java.util.UUID
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * M23 Android substrate tests. Only creates disposable fixtures under the app's
 * private cache. Does not inspect or modify actual game/Steam/SAF/storage paths.
 * Device result is M23_SYNTHETIC_ANDROID, NOT real-installation qualification.
 */
@RunWith(AndroidJUnit4::class)
class M23DiscoveryDeviceTest {
    private lateinit var root: File
    private lateinit var ownedParent: File
    private val marker = ".cinderbox-m23-synthetic-owned"
    private val cores = listOf("Stardew Valley.dll", "StardewValley.GameData.dll",
        "BmFont.dll", "xTile.dll", "Lidgren.Network.dll")

    @Before fun setup() {
        val app = InstrumentationRegistry.getInstrumentation().targetContext
        ownedParent = app.cacheDir.canonicalFile
        root = File(ownedParent, "m23-owned-${UUID.randomUUID()}")
        assertTrue("Private fixture allocation failed", root.mkdir())
        File(root, marker).writeText("cinderbox-m23-owned-fixture-v1\n")
    }

    @After fun cleanup() {
        if (!::root.isInitialized || !root.exists()) return
        // Refuse cleanup unless the fresh fixture is still owned and within cache.
        val canonicalParent = root.parentFile?.canonicalFile
        val owns = canonicalParent == ownedParent && root.name.startsWith("m23-owned-") &&
            File(root, marker).takeIf { it.isFile && !Files.isSymbolicLink(it.toPath()) }
                ?.readText() == "cinderbox-m23-owned-fixture-v1\n"
        if (owns) assertTrue("Owned fixture cleanup failed", root.deleteRecursively())
        else fail("Synthetic fixture ownership changed; preserve for investigation")
    }

    private fun game(where: File) {
        assertTrue(where.mkdirs() || where.isDirectory)
        cores.forEach { File(where, it).writeText("synthetic-content-not-a-game") }
        val content = File(where, "Content")
        assertTrue(content.mkdir())
        File(content, "fixture.xnb").writeText("synthetic")
    }

    @Test fun m23_01MissingPrivatePathsAreNotDownloadApproval() {
        val i = M23InstallationDiscovery.inspect(File(root, "not-selected"), root)
        assertEquals(M23InstallationDiscovery.Status.MISSING, i.modern.status)
        assertEquals(M23InstallationDiscovery.Status.MISSING, i.legacy.status)
        assertFalse(i.downloadAllowed)
        assertFalse(i.writesPerformed)
    }

    @Test fun m23_02ModernCandidateCannotBecomeVerified() {
        game(File(root, "desktop/GameFiles"))
        val i = M23InstallationDiscovery.inspect(File(root, "absent"), root)
        assertEquals(M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED, i.modern.status)
        assertFalse(i.modern.verified)
        assertFalse(i.modern.canInstallOrOverwrite)
        assertEquals("UNKNOWN_NO_AUTHENTICATED_MANIFEST", i.modern.version)
        assertTrue(i.gameAlreadyPresent)
    }

    @Test fun m23_03LegacyModernCollisionStaysUnresolved() {
        game(File(root, "GameFiles"))
        game(File(root, "desktop/GameFiles"))
        val before = File(root, "GameFiles/Stardew Valley.dll").readBytes()
        val i = M23InstallationDiscovery.inspect(root, root)
        assertTrue(i.layoutConflict)
        assertFalse(i.downloadAllowed)
        assertArrayEquals(before, File(root, "GameFiles/Stardew Valley.dll").readBytes())
    }

    @Test fun m23_04StagingRequiresExplicitRecoveryReview() {
        game(File(root, "desktop/GameFiles"))
        val stage = File(root, "desktop/GameFiles/.sdvsync-stage-test")
        stage.mkdir()
        val i = M23InstallationDiscovery.inspect(root, root)
        assertEquals(M23InstallationDiscovery.Status.RECOVERY_REVIEW, i.modern.status)
        assertFalse(i.modern.canInstallOrOverwrite)
        assertTrue(stage.isDirectory)
    }

    @Test fun m23_05UntrustedZipIsOnlyPartial() {
        val dir = File(root, "desktop/GameFiles")
        assertTrue(dir.mkdirs())
        File(dir, "unknown.zip").writeText("synthetic-archive")
        val i = M23InstallationDiscovery.inspect(root, root)
        assertEquals(M23InstallationDiscovery.Status.PARTIAL, i.modern.status)
        assertTrue(i.modern.evidence.contains(M23InstallationDiscovery.Evidence.UNTRUSTED_ARCHIVE))
        assertFalse(i.downloadAllowed)
    }

    @Test fun m23_06SmapiStageNotMisreportedAsHealthy() {
        val smapi = File(root, "smapi-internal")
        assertTrue(smapi.mkdir())
        File(smapi, "SMAPI.dll").writeText("synthetic")
        assertEquals(M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED,
            M23InstallationDiscovery.inspect(root, root).smapi.status)
        assertTrue(File(root, ".smapi-internal.sdvsync-backup").mkdir())
        assertEquals(M23InstallationDiscovery.Status.RECOVERY_REVIEW,
            M23InstallationDiscovery.inspect(root, root).smapi.status)
    }

    @Test fun m23_07SymlinkToFixtureIsRejected() {
        val outside = File(root, "outside")
        game(outside)
        val link = File(root, "desktop/GameFiles")
        assertTrue(link.parentFile!!.mkdirs())
        Files.createSymbolicLink(link.toPath(), outside.toPath())
        val i = M23InstallationDiscovery.inspect(link, root)
        assertEquals(M23InstallationDiscovery.Status.UNSAFE_LINK, i.modern.status)
        assertFalse(i.modern.verified)
    }

    @Test fun m23_08BoundedEnumerationFailsClosed() {
        val dir = File(root, "desktop/GameFiles")
        assertTrue(dir.mkdirs())
        repeat(M23InstallationDiscovery.MAX_CHILDREN + 1) { n ->
            File(dir, "item-$n").writeText("x")
        }
        val i = M23InstallationDiscovery.inspect(dir, root)
        assertEquals(M23InstallationDiscovery.Status.INACCESSIBLE, i.modern.status)
        assertFalse(i.downloadAllowed)
    }

    @Test fun m23_09HealthReadDoesNotWriteProbeOrMutateExisting() {
        val selected = File(root, "selected")
        assertTrue(selected.mkdir())
        File(selected, "sentinel.txt").writeText("do-not-touch")
        val before = selected.list()?.toSet()
        val scanned = InstallationScanner.scan(selected, false, root)
        assertNotNull(scanned.discovery)
        assertFalse(scanned.discovery!!.writesPerformed)
        assertFalse(scanned.storage.writable)
        assertEquals(before, selected.list()?.toSet())
        assertEquals("do-not-touch", File(selected, "sentinel.txt").readText())
    }

    @Test fun m23_10SelectedArchiveWrapperIsUnverified() {
        val selected = File(root, "selected")
        game(File(selected, "Stardew Valley"))
        val i = M23InstallationDiscovery.inspect(selected, root)
        assertEquals(M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED, i.selected.status)
        assertFalse(i.selected.verified)
        assertFalse(i.downloadAllowed)
    }
}
