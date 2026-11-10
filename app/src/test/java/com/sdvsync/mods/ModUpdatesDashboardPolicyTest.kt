package com.sdvsync.mods

import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModManifest
import com.sdvsync.mods.models.ModUpdateInfo
import org.junit.Assert.*
import org.junit.Test

/** Current canonical update dashboard model; never uses network or filesystem. */
class ModUpdatesDashboardPolicyTest {
    private val now = 30_000_000L
    private fun mod(id: String = "Author.Mod", version: String = "1.2.0",
                    enabled: Boolean = true, key: String = "Nexus:50535") = InstalledMod(
        ModManifest("Mod", "Author", version, id, "Test", updateKeys = listOf(key)),
        "Test", "synthetic", enabled)
    private fun obs() = mapOf("author.mod" to
        ModUpdateObservation("Author.Mod", "1.2.0", "1.3.0", UpdateAssessment.NEWER))
    private fun dashboard(mods: List<InstalledMod> = listOf(mod()),
                          checkedAt: Long = now - 1000L,
                          ignored: Map<String, ModUpdateInfo> = emptyMap()) =
        ModUpdatesDashboardPolicy.evaluate(mods, obs(), ignored, checkedAt, now)

    @Test fun freshCacheExposesOnlyComparableModUpdate() {
        val view = dashboard()
        assertEquals("SMAPI_CACHE_FRESH", view.freshness)
        assertEquals(1, view.availableCount)
        assertEquals("NEWER", view.entries.single().status)
        assertEquals("1.3.0", view.entries.single().candidateVersion)
        assertEquals("50535", view.entries.single().nexusModId)
    }
    @Test fun exactFourHourBoundaryStillFreshAndOneMillisecondOlderUnknown() {
        assertEquals(1, dashboard(checkedAt = now - NexusUpdateEvidence.FRESH_MS).availableCount)
        val stale = dashboard(checkedAt = now - NexusUpdateEvidence.FRESH_MS - 1)
        assertEquals("SMAPI_CACHE_STALE", stale.freshness)
        assertEquals(0, stale.availableCount)
        assertEquals("UNKNOWN", stale.entries.single().status)
        assertEquals(0, dashboard(checkedAt = now + 1).availableCount)
    }
    @Test fun disabledAndDuplicateIdsFailClosed() {
        assertEquals("DISABLED", dashboard(listOf(mod(enabled = false))).entries.single().status)
        val duplicate = dashboard(listOf(mod(), mod(id = "AUTHOR.MOD")))
        assertEquals(0, duplicate.availableCount)
        assertTrue(duplicate.entries.all { it.status == "AMBIGUOUS" })
    }
    @Test fun ignoreAppliesOnlyToMatchingInstalledAndCandidateVersions() {
        val match = ModUpdateInfo("Author.Mod", "1.2.0", "1.3.0", null, "Nexus:50535")
        val view = dashboard(ignored = mapOf("author.mod" to match))
        assertEquals(0, view.availableCount)
        assertEquals(1, view.ignoredCount)
        assertTrue(view.entries.single().ignored)
        val different = match.copy(latestVersion = "1.4.0")
        assertEquals(1, dashboard(ignored = mapOf("author.mod" to different)).availableCount)
    }
    @Test fun forgedCandidateAndMalformedNexusIdentityAreNeverActionable() {
        val status = ModUpdatesDashboardPolicy.evaluate(listOf(mod(key = "Nexus:0")),
            mapOf("author.mod" to ModUpdateObservation("Author.Mod", "1.2.0", "nxm://secret",
                UpdateAssessment.NEWER)), emptyMap(), now - 1000L, now)
        assertEquals(0, status.availableCount)
        assertEquals("UNKNOWN", status.entries.single().status)
        assertNull(status.entries.single().nexusModId)
    }
}
