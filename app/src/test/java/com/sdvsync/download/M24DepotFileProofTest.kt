package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

class M24DepotFileProofTest {
    private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-1").digest(bytes).joinToString("") { "%02x".format(it) }
    private fun fixture(block: (File, Map<String, M24DepotFileProof.FileEntry>) -> Unit) {
        val root = Files.createTempDirectory("m24-file-proof-").toFile()
        try {
            val bytes = "synthetic-stardew-data".toByteArray()
            val file = File(root, "Content/fixture.bin")
            check(file.parentFile.mkdirs())
            file.writeBytes(bytes)
            block(root, mapOf("Content/fixture.bin" to M24DepotFileProof.FileEntry(bytes.size.toLong(), digest(bytes))))
        } finally { assertTrue(root.deleteRecursively()) }
    }
    private fun fails(block: () -> Unit) {
        try { block(); fail("Expected rejection") }
        catch (_: IllegalStateException) { }
        catch (_: IllegalArgumentException) { }
    }
    @Test fun correctManifestMatchesOnlyOwnedStage() = fixture { root, expected ->
        File(root, ".DepotDownloader").mkdir()
        File(root, ".DepotDownloader/123_456.manifest").writeText("metadata")
        assertEquals(1, M24DepotFileProof.verify(root, expected).files)
    }
    @Test fun corruptedStageFails() = fixture { root, expected ->
        File(root, "Content/fixture.bin").writeText("different")
        fails { M24DepotFileProof.verify(root, expected) }
    }
    @Test fun unexpectedStageFileFails() = fixture { root, expected ->
        File(root, "evil.bin").writeText("extra")
        fails { M24DepotFileProof.verify(root, expected) }
    }
    @Test fun traversalAndMissingManifestEntryFail() = fixture { root, expected ->
        fails { M24DepotFileProof.verify(root, mapOf("../outside" to expected.values.first())) }
        fails { M24DepotFileProof.verify(root, emptyMap()) }
    }
}
