package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

class NexusLab03CPolicyTest {
    @Test fun exactBoundedOfficialFilePageHint() {
        assertEquals(
            "https://www.nexusmods.com/stardewvalley/mods/995000001?tab=files&file_id=123456789",
            NexusLab03CPolicy.reviewUrl("995000001", "123456789", 1000L, 1001L)
        )
        val url = requireNotNull(NexusLab03CPolicy.canonicalUrl("995000001", "123456789"))
        assertFalse(url.contains("cinderbox_"))
        assertFalse(url.contains("nxm"))
        assertFalse(url.contains("key="))
        assertFalse(url.contains("expires="))
    }

    @Test fun refusesChangedOrUnverifiedIdentity() {
        for (bad in listOf("", "0", "01", "-1", "1/2", "1?tab=", "1234567890123", "abc")) {
            assertNull(NexusLab03CPolicy.canonicalUrl(bad, "123"))
            assertNull(NexusLab03CPolicy.canonicalUrl("123", bad))
        }
    }

    @Test fun deniesFutureAndExpiredPendingRequests() {
        val maxAge = NexusLab03CPolicy.MAX_REQUEST_AGE_MS
        assertNotNull(NexusLab03CPolicy.reviewUrl("1", "2", 1000L, 1000L + maxAge))
        assertNull(NexusLab03CPolicy.reviewUrl("1", "2", 1000L, 1001L + maxAge))
        assertNull(NexusLab03CPolicy.reviewUrl("1", "2", 1001L, 1000L))
        assertNull(NexusLab03CPolicy.reviewUrl("1", "2", 0L, 1000L))
        assertNull(NexusLab03CPolicy.reviewUrl("1", "2", 1L, 0L))
    }
}
