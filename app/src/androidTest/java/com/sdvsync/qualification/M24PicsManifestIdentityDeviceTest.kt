package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.download.GameDownloadRecovery
import com.sdvsync.download.M24DepotManifestIdentity
import java.io.File
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic, private app-cache fixtures only: no Steam account or game storage. */
@RunWith(AndroidJUnit4::class)
class M24PicsManifestIdentityDeviceTest {
    private fun owned(block: (GameDownloadRecovery, File) -> Unit) {
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        val root = File(cache, "m24pics-owned-${UUID.randomUUID()}")
        assertTrue(root.mkdir())
        val owner = File(root, "owner").apply { assertTrue(mkdir()) }
        val destination = File(root, "game")
        try { block(GameDownloadRecovery(owner), destination) }
        finally {
            assertEquals(cache, root.canonicalFile.parentFile)
            assertTrue(root.name.startsWith("m24pics-owned-"))
            assertTrue(root.deleteRecursively())
        }
    }
    private fun reject(block: () -> Unit) {
        try { block(); fail("Expected fail-closed rejection") }
        catch (_: IllegalStateException) { }
    }
    @Test fun m24p_01ManifestIdentityBoundAndPersisted() = owned { r, target ->
        r.beginStaged(target, "public", "windows", true)
        r.bindSteamBuildId(88)
        val id = M24DepotManifestIdentity.snapshot("public", 88, mapOf(20 to "707")).fingerprint
        r.bindDepotManifestFingerprint(id)
        GameDownloadRecovery(File(target.parentFile, "owner")).requireDepotManifestFingerprint(id)
    }
    @Test fun m24p_02DepotManifestDriftPreservesPartialStage() = owned { r, target ->
        r.beginStaged(target, "public", "windows", true)
        r.bindSteamBuildId(88)
        val id = M24DepotManifestIdentity.snapshot("public", 88, mapOf(20 to "707")).fingerprint
        r.bindDepotManifestFingerprint(id)
        val file = File(r.requireActiveStage(target), "part.bin").apply { writeText("keep") }
        reject { r.bindDepotManifestFingerprint("0".repeat(64)) }
        assertEquals("keep", file.readText())
        assertFalse(target.exists())
    }
    @Test fun m24p_03UnboundManifestCannotQualifyCheckpoint() = owned { r, target ->
        r.beginStaged(target, "public", "windows", true)
        r.bindSteamBuildId(88)
        reject { r.requireDepotManifestFingerprint("a".repeat(64)) }
    }
    @Test fun m24p_04MalformedManifestRejectedWithoutWrites() = owned { r, target ->
        r.beginStaged(target, "public", "windows", true)
        r.bindSteamBuildId(88)
        try { M24DepotManifestIdentity.snapshot("public", 88, mapOf(0 to "123")); fail("Invalid depot") }
        catch (_: IllegalArgumentException) { }
        assertFalse(target.exists())
    }
}
