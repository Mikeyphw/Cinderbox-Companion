package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

class ModUpdateInsightTest {
    @Test fun statusesAreExplicitAndUnknownNeverEqualsCurrent() {
        assertEquals("Update available", ModUpdateInsight.label(UpdateAssessment.NEWER))
        assertEquals("Update status unknown", ModUpdateInsight.label(UpdateAssessment.UNKNOWN))
        assertEquals("Installed version ahead", ModUpdateInsight.label(UpdateAssessment.INSTALLED_AHEAD))
    }

    @Test fun staleClockNeverLooksFresh() {
        assertEquals("Never checked", ModUpdateInsight.freshness(0, 100_000))
        assertTrue(ModUpdateInsight.freshness(100, 100).startsWith("Checked"))
        assertTrue(ModUpdateInsight.freshness(500, 400).contains("invalid"))
        assertTrue(ModUpdateInsight.freshness(10, ModUpdateInsight.STALE_AFTER_MS + 11)
            .contains("expired"))
    }

    @Test fun statusIsInvalidWhenInstalledVersionChanged() {
        val statuses = mapOf("example.mod" to ModUpdateObservation("Example.Mod", "1.0", "2.0", UpdateAssessment.NEWER))
        assertNotNull(ModUpdateInsight.observationFor("EXAMPLE.MOD", "1.0", statuses))
        assertNull(ModUpdateInsight.observationFor("Example.Mod", "2.0", statuses))
    }

    @Test fun untrustedChangelogIsPlainTextAndBounded() {
        val raw = "<style>evil</style><script>steal()</script><p>Fixed &amp; improved</p>" + "Z".repeat(100_000)
        val safe = ModUpdateInsight.plainChangelog(raw)!!
        assertTrue(safe.contains("Fixed & improved"))
        assertFalse(safe.contains("steal"))
        assertTrue(safe.length <= ModUpdateInsight.MAX_CHANGELOG_DISPLAY)
        assertNull(ModUpdateInsight.plainChangelog(null))
    }

    @Test fun externalLinksMustBeTrustworthyHttps() {
        assertNotNull(ModUpdateInsight.safeUpdateUrl("https://www.nexusmods.com/stardewvalley/mods/123"))
        for (bad in listOf("javascript:alert(1)", "file:///etc/passwd", "http://github.com/owner",
            "https://127.0.0.1/foo", "https://evil.com/payload", "https://u:p@github.com/x")) {
            assertNull(bad, ModUpdateInsight.safeUpdateUrl(bad))
        }
    }
}
