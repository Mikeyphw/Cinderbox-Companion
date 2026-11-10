package com.sdvsync.mods

import java.util.Locale

/**
 * CB-NX04C: bounded, non-networked interpretation of an existing SMAPI observation.
 * Browser requests NEVER initiate a provider lookup. This snapshot is only an
 * application-owned record of a prior successful SMAPI check, not a Nexus file proof.
 */
internal object NexusUpdateEvidence {
    const val FRESH_MS = 4 * 60 * 60 * 1000L

    data class Snapshot(
        val checkedAtMs: Long = 0L,
        val observations: Map<String, ModUpdateObservation> = emptyMap(),
        val available: Boolean = true
    )
    data class Decision(val status: String, val candidate: String? = null)

    fun freshness(snapshot: Snapshot, nowMs: Long): String = when {
        !snapshot.available -> "UNAVAILABLE"
        snapshot.checkedAtMs <= 0L -> "NOT_PERFORMED"
        nowMs <= 0L || snapshot.checkedAtMs > nowMs -> "CLOCK_INVALID"
        nowMs - snapshot.checkedAtMs > FRESH_MS -> "SMAPI_CACHE_STALE"
        else -> "SMAPI_CACHE_FRESH"
    }

    /** Per exact installed SMAPI ID/version; anything ambiguous becomes UNKNOWN. */
    fun classify(snapshot: Snapshot, id: String, installedVersion: String, nowMs: Long): Decision {
        if (freshness(snapshot, nowMs) != "SMAPI_CACHE_FRESH") return Decision("UNKNOWN")
        val canonical = runCatching { ModUpdatePolicy.normalizedId(id) }.getOrNull()
            ?: return Decision("UNKNOWN")
        val obs = snapshot.observations[canonical] ?: return Decision("UNKNOWN")
        if (obs.installedVersion != installedVersion ||
            runCatching { ModUpdatePolicy.normalizedId(obs.uniqueID) }.getOrNull() != canonical) {
            return Decision("UNKNOWN")
        }
        val candidate = obs.candidateVersion
        val valid = candidate == null || (candidate.length in 1..80 &&
            candidate.matches(Regex("[A-Za-z0-9.+_-]{1,80}")))
        if (!valid) return Decision("UNKNOWN")
        val assessed = runCatching { ModUpdatePolicy.assess(installedVersion, candidate) }.getOrNull()
            ?: return Decision("UNKNOWN")
        if (assessed != obs.status) return Decision("UNKNOWN")
        // A candidate must be both meaningful and strictly newer for an actionable badge.
        return when (assessed) {
            UpdateAssessment.NEWER -> Decision("NEWER", candidate)
            UpdateAssessment.CURRENT -> Decision("CURRENT")
            UpdateAssessment.INSTALLED_AHEAD -> Decision("INSTALLED_AHEAD")
            UpdateAssessment.UNCOMPARABLE -> Decision("UNCOMPARABLE")
            UpdateAssessment.UNKNOWN -> Decision("UNKNOWN")
        }
    }
}
