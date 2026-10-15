package com.sdvsync.sync

import com.sdvsync.diagnostics.SyncOperationDiagnostics
import com.sdvsync.diagnostics.SyncTelemetryDirection
import com.sdvsync.diagnostics.SyncTelemetryOutcome
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

class SyncChangePreviewTest {
    private fun stamp(name: String, value: String): CloudFileStamp = CloudFileStamp(name,
        value.toByteArray().size.toLong(), MessageDigest.getInstance("SHA-1")
            .digest(value.toByteArray()).joinToString("") { "%02x".format(it) }, 123, "remote")

    @Test fun previewListsActualWritesWithoutProposingDeletes() {
        val p = SyncChangePreviewBuilder.build("Save_123", SyncPreviewDirection.PUSH, false,
            mapOf("main" to "new".toByteArray()), listOf(stamp("main", "old"), stamp("remoteOnly", "keep")))
        assertEquals(SyncPreviewAction.OVERWRITE, p.files.first { it.name == "main" }.action)
        assertEquals(SyncPreviewAction.PRESERVE, p.files.first { it.name == "remoteOnly" }.action)
        assertEquals(1, p.writeCount)
    }
    @Test fun pullAddsCloudOnlyAndPreservesLocalOnly() {
        val p = SyncChangePreviewBuilder.build("Save_123", SyncPreviewDirection.PULL, false,
            mapOf("localOnly" to byteArrayOf(1)), listOf(stamp("cloudOnly", "hello")))
        assertEquals(SyncPreviewAction.ADD, p.files.first { it.name == "cloudOnly" }.action)
        assertEquals(SyncPreviewAction.PRESERVE, p.files.first { it.name == "localOnly" }.action)
    }
    @Test fun aChangedLocalByteOrCloudStampInvalidatesPreview() {
        val a = SyncChangePreviewBuilder.build("Save_123", SyncPreviewDirection.PUSH, false,
            mapOf("main" to byteArrayOf(1)), listOf(stamp("main", "old")))
        val b = SyncChangePreviewBuilder.build("Save_123", SyncPreviewDirection.PUSH, false,
            mapOf("main" to byteArrayOf(2)), listOf(stamp("main", "old")))
        assertNotEquals(a.fingerprint, b.fingerprint)
        val c = SyncChangePreviewBuilder.build("Save_123", SyncPreviewDirection.PUSH, false,
            mapOf("main" to byteArrayOf(1)), listOf(stamp("main", "new")))
        assertNotEquals(a.fingerprint, c.fingerprint)
    }
    @Test fun duplicateCloudPathsAndUntrustedNamesFailClosed() {
        assertThrows(IllegalArgumentException::class.java) {
            SyncChangePreviewBuilder.build("a", SyncPreviewDirection.PULL, false,
                emptyMap(), listOf(stamp("x", "1"), stamp("x", "2")))
        }
        assertThrows(IllegalArgumentException::class.java) {
            SyncChangePreviewBuilder.build("a", SyncPreviewDirection.PUSH, false,
                mapOf("../evil" to byteArrayOf(1)), emptyList())
        }
    }
    @Test fun diagnosticCodesAreCategoricalNotRawExceptionText() {
        SyncOperationDiagnostics.record(SyncTelemetryDirection.PUSH, SyncTelemetryOutcome.ERROR,
            "secret-token-and-save-name")
        assertEquals("UNKNOWN", SyncOperationDiagnostics.snapshot().last().errorCode)
    }
}
