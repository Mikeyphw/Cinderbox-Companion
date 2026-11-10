package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

class NexusCompanionPrivacyPolicyTest {
    @Test fun masksExactIdentitiesWithoutGuessingInvalidOnes() {
        assertEquals("••••39", NexusCompanionPrivacyPolicy.redactedId("178239"))
        assertEquals("unknown", NexusCompanionPrivacyPolicy.redactedId("nxm://secret"))
        assertEquals("unknown", NexusCompanionPrivacyPolicy.redactedId("0"))
        assertEquals("••••", NexusCompanionPrivacyPolicy.redactedId("12"))
    }

    @Test fun reportContainsOnlyFixedEnumsAndCounts() {
        val report = NexusCompanionPrivacyPolicy.report("0.1.1", 123L, true, true,
            true, true, listOf("PENDING", "OPENED", "DISMISSED"), true,
            listOf("VERIFY_REQUIRED", "INSTALLED", "QUEUED"))
        assertTrue(report.contains("\"handoff_allowed\":true"))
        assertTrue(report.contains("\"PENDING\":1"))
        assertTrue(report.contains("\"VERIFY_REQUIRED\":1"))
        assertTrue(report.contains("\"bridge_protocol\":1"))
        assertFalse(report.contains("mod_id"))
        assertFalse(report.contains("file_id"))
    }

    @Test fun untrustedFieldsCannotBeExported() {
        val bearer = "nxm://bad-secret?key=TOKEN"
        val path = "/sdcard/secret/provider-headers"
        val report = NexusCompanionPrivacyPolicy.report(bearer, 1L, false, false, true,
            false, listOf(bearer), false, listOf(path))
        assertFalse(report.contains("TOKEN"))
        assertFalse(report.contains("nxm://"))
        assertFalse(report.contains("/sdcard"))
        assertTrue(report.contains("\"app_version\":\"unknown\""))
        assertTrue(report.contains("\"inbox_state\":\"UNAVAILABLE\""))
        assertTrue(report.contains("\"handoff_allowed\":false"))
    }

    @Test fun corruptOrUnknownHistoryMustNotBeRepresentedAsVerifiedZero() {
        val report = NexusCompanionPrivacyPolicy.report("1.2", 42, true, false, false,
            false, listOf("PENDING"), false, listOf("INSTALLED"))
        assertTrue(report.contains("\"inbox_state\":\"UNAVAILABLE\""))
        assertTrue(report.contains("\"journal_state\":\"UNAVAILABLE\""))
        assertTrue(report.contains("\"inbox_counts\":null"))
        assertTrue(report.contains("\"job_counts\":null"))
        assertFalse(report.contains("\"PENDING\":1"))
        assertFalse(report.contains("\"INSTALLED\":1"))
    }

    @Test fun onlyWhitelistedJobStatesAreCounted() {
        val report = NexusCompanionPrivacyPolicy.report("2.1-beta", -7, true, true,
            false, true, listOf("OPENED", "IMPORTED"), true,
            listOf("QUEUED", "INSTALLED", "Bearer secret", "QUEUED"))
        assertTrue(report.contains("\"QUEUED\":2"))
        assertTrue(report.contains("\"INSTALLED\":1"))
        assertTrue(report.contains("\"observed_at_ms\":0"))
        assertFalse(report.contains("Bearer"))
        assertFalse(report.contains("IMPORTED"))
    }
}
