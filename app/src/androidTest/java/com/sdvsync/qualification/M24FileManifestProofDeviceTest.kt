package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.download.M24DepotFileProof
import java.io.File
import java.security.MessageDigest
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Owned app-cache test fixtures. No live account or shared Cinderbox files. */
@RunWith(AndroidJUnit4::class)
class M24FileManifestProofDeviceTest {
    private fun owned(block: (File, Map<String, M24DepotFileProof.FileEntry>) -> Unit) {
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        val stage = File(cache, "m24files-owned-${UUID.randomUUID()}")
        assertTrue(stage.mkdir())
        val payload = "private manifest fixture".toByteArray()
        val file = File(stage, "Content/fixture.bin")
        assertTrue(file.parentFile!!.mkdirs())
        file.writeBytes(payload)
        val digest = MessageDigest.getInstance("SHA-1").digest(payload).joinToString("") { "%02x".format(it) }
        try { block(stage, mapOf("Content/fixture.bin" to M24DepotFileProof.FileEntry(payload.size.toLong(),digest))) }
        finally { assertEquals(cache, stage.canonicalFile.parentFile); assertTrue(stage.deleteRecursively()) }
    }
    private fun reject(block: () -> Unit) {
        try { block(); fail("Expected fail-closed error") }
        catch (_: IllegalArgumentException) { }
        catch (_: IllegalStateException) { }
    }
    @Test fun m24f_01OwnedStageMatchesManifest() = owned { stage, entries ->
        assertEquals(1, M24DepotFileProof.verify(stage, entries).files)
    }
    @Test fun m24f_02AlteredBytesCannotQualify() = owned { stage, entries ->
        File(stage, "Content/fixture.bin").writeText("tampered bytes")
        reject { M24DepotFileProof.verify(stage, entries) }
    }
    @Test fun m24f_03UnexpectedFileCannotQualify() = owned { stage, entries ->
        File(stage, "unlisted.bin").writeText("unlisted")
        reject { M24DepotFileProof.verify(stage, entries) }
    }
    @Test fun m24f_04TraversalIsRejectedWithoutOutsideWrites() = owned { stage, entries ->
        reject { M24DepotFileProof.verify(stage, mapOf("../outside.bin" to entries.values.first())) }
        assertFalse(File(stage.parentFile, "outside.bin").exists())
    }
}
