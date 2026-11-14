package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

class NexusLab03DArchivePolicyTest {
    private val hash = "a".repeat(64)
    private fun ok(
        schema: String = NexusLab03DArchivePolicy.STAGE_SCHEMA,
        scope: String = NexusLab03DArchivePolicy.SCOPE,
        source: String = hash, stage: String = hash,
        size: Long = 900L, stagedSize: Long = 900L,
        provenance: String = NexusLab03DArchivePolicy.PROVENANCE,
        nexusVerified: Boolean = false, installed: Boolean = false,
        productionExamined: Boolean = false
    ) = NexusLab03DArchivePolicy.validLocalReceipt(
        schema, scope, source, stage, size, stagedSize, provenance,
        nexusVerified, installed, productionExamined)

    @Test fun permitsOnlyBoundedSourceMatchedLocalSyntheticEvidence() {
        assertTrue(ok())
        assertTrue(ok(size = NexusLab03DArchivePolicy.MIN_ARCHIVE_BYTES,
            stagedSize = NexusLab03DArchivePolicy.MIN_ARCHIVE_BYTES))
        assertTrue(ok(size = NexusLab03DArchivePolicy.MAX_ARCHIVE_BYTES,
            stagedSize = NexusLab03DArchivePolicy.MAX_ARCHIVE_BYTES))
    }

    @Test fun refusesProvenanceEscalation() {
        assertFalse(ok(schema = "cbnx06-live-nexus-v1"))
        assertFalse(ok(scope = "LIVE_NEXUS"))
        assertFalse(ok(provenance = "NEXUS_VERIFIED"))
        assertFalse(ok(nexusVerified = true))
        assertFalse(ok(installed = true))
        assertFalse(ok(productionExamined = true))
    }

    @Test fun refusesHashAndSizeDrift() {
        assertFalse(ok(source = "A".repeat(64)))
        assertFalse(ok(stage = "b".repeat(64)))
        assertFalse(ok(source = "a".repeat(63)))
        assertFalse(ok(size = 127L, stagedSize = 127L))
        assertFalse(ok(size = 16385L, stagedSize = 16385L))
        assertFalse(ok(stagedSize = 899L))
    }
}
