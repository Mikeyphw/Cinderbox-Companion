package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

/** Unit-level policy regression: no HTTP, credentials, or game filesystem. */
class NexusUpdateEvidenceTest {
    private val now = 20_000_000L
    private fun snap(at: Long = now - 1000L, version: String = "1.2.0",
                     candidate: String? = "1.3.0", status: UpdateAssessment = UpdateAssessment.NEWER) =
        NexusUpdateEvidence.Snapshot(at, mapOf("author.mod" to
            ModUpdateObservation("Author.Mod", version, candidate, status)))

    @Test fun freshComparedNewerVersionIsModOnly() {
        val result = NexusUpdateEvidence.classify(snap(), "AUTHOR.mod", "1.2.0", now)
        assertEquals("NEWER", result.status)
        assertEquals("1.3.0", result.candidate)
        assertEquals("SMAPI_CACHE_FRESH", NexusUpdateEvidence.freshness(snap(), now))
    }

    @Test fun noProviderObservationOrExpiredTimestampCannotCreateBadge() {
        assertEquals("NOT_PERFORMED", NexusUpdateEvidence.freshness(
            NexusUpdateEvidence.Snapshot(), now))
        assertEquals("SMAPI_CACHE_STALE", NexusUpdateEvidence.freshness(snap(1L), now))
        assertEquals("CLOCK_INVALID", NexusUpdateEvidence.freshness(snap(now + 1L), now))
        assertEquals("UNAVAILABLE", NexusUpdateEvidence.freshness(
            NexusUpdateEvidence.Snapshot(available = false), now))
        assertEquals("UNKNOWN", NexusUpdateEvidence.classify(snap(1L), "author.mod", "1.2.0", now).status)
    }

    @Test fun fourHoursIsInclusiveAndNextMillisecondIsStale() {
        val checkedAt = 999_000L
        val fourHours = 4L * 60L * 60L * 1000L
        assertEquals(14_400_000L, fourHours)
        assertEquals(fourHours, NexusUpdateEvidence.FRESH_MS)
        val atBoundary = snap(at = checkedAt)
        assertEquals("SMAPI_CACHE_FRESH", NexusUpdateEvidence.freshness(
            atBoundary, checkedAt + fourHours))
        val permitted = NexusUpdateEvidence.classify(atBoundary, "author.mod", "1.2.0",
            checkedAt + fourHours)
        assertEquals("NEWER", permitted.status)
        assertEquals("1.3.0", permitted.candidate)
        assertEquals("SMAPI_CACHE_STALE", NexusUpdateEvidence.freshness(
            atBoundary, checkedAt + fourHours + 1L))
        val denied = NexusUpdateEvidence.classify(atBoundary, "author.mod", "1.2.0",
            checkedAt + fourHours + 1L)
        assertEquals("UNKNOWN", denied.status)
        assertNull(denied.candidate)
    }

    @Test fun installedVersionMismatchFailsClosed() {
        assertEquals("UNKNOWN", NexusUpdateEvidence.classify(snap(version = "1.2.1"),
            "author.mod", "1.2.0", now).status)
    }

    @Test fun forgedAssessmentAndCredentialStringCannotEscape() {
        assertEquals("UNKNOWN", NexusUpdateEvidence.classify(
            snap(candidate = "1.1.0", status = UpdateAssessment.NEWER),
            "author.mod", "1.2.0", now).status)
        val rejected = NexusUpdateEvidence.classify(
            snap(candidate = "nxm://secret", status = UpdateAssessment.NEWER),
            "author.mod", "1.2.0", now)
        assertEquals("UNKNOWN", rejected.status)
        assertNull(rejected.candidate)
    }

    @Test fun sameVersionCanBeCurrentWithoutExactFileClaim() {
        val decision = NexusUpdateEvidence.classify(snap(candidate = "1.2.0",
            status = UpdateAssessment.CURRENT), "author.mod", "1.2.0", now)
        assertEquals("CURRENT", decision.status)
        assertNull(decision.candidate)
    }
}
