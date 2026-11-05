package com.sdvsync.mods

import com.sdvsync.mods.models.ModUpdateInfo
import org.junit.Assert.*
import org.junit.Test

class ModUpdatePolicyTest {
    private fun status(a: String, b: String?) = ModUpdatePolicy.assess(a, b)
    @Test fun semanticOrderingAndAhead() {
        assertEquals(UpdateAssessment.NEWER, status("1.2", "1.10"))
        assertEquals(UpdateAssessment.INSTALLED_AHEAD, status("2.0", "1.9"))
        assertEquals(UpdateAssessment.CURRENT, status("1.2", "1.2.0"))
        assertEquals(UpdateAssessment.NEWER, status("1.0-beta.2", "1.0-beta.10"))
        assertEquals(UpdateAssessment.NEWER, status("1.0-rc.1", "1.0"))
        assertEquals(UpdateAssessment.INSTALLED_AHEAD, status("1.0", "1.0-alpha"))
        assertEquals(UpdateAssessment.CURRENT, status("1.2.3+abc", "1.2.3+def"))
    }
    @Test fun nonSemverAndUnknownAreNotUpdates() {
        assertEquals(UpdateAssessment.UNCOMPARABLE, status("1.0", "v2"))
        assertEquals(UpdateAssessment.UNCOMPARABLE, status("nightly", "next"))
        assertEquals(UpdateAssessment.UNCOMPARABLE, status("1.2", "01.3"))
        assertEquals(UpdateAssessment.UNKNOWN, status("1.0", null))
        assertEquals(UpdateAssessment.CURRENT, status("custom", "custom"))
    }
    @Test fun ignoreExactlyOneVersionAndCanonicalId() {
        fun mod(v: String) = ModUpdateInfo("Author.Mod", "1.0", v, null, "Nexus:123")
        val ignore = mapOf("author.mod" to "2.0")
        assertTrue(ModUpdatePolicy.isIgnored(mod("2.0"), ignore))
        assertFalse(ModUpdatePolicy.isIgnored(mod("2.1"), ignore))
        assertTrue(ModUpdatePolicy.actionable(mapOf("Author.Mod" to mod("2.0")), ignore).isEmpty())
        assertEquals(1, ModUpdatePolicy.actionable(mapOf("Author.Mod" to mod("2.1")), ignore).size)
        assertEquals(1, ModUpdatePolicy.ignored(mapOf("Author.Mod" to mod("2.0")), ignore).size)
    }
    @Test fun invalidCandidateAndModIdentifiersAreRefused() {
        assertTrue(runCatching { ModUpdatePolicy.checkedCandidateVersion("\u0000") }.isFailure)
        assertTrue(runCatching { ModUpdatePolicy.normalizedId("../path/mod") }.isFailure)
        assertTrue(runCatching { ModUpdatePolicy.normalizedId(" ") }.isFailure)
    }
}
