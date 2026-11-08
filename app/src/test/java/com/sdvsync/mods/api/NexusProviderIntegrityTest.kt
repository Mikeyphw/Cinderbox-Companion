package com.sdvsync.mods.api

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** No network, Nexus credentials, filesystem changes or Android runtime required. */
class NexusProviderIntegrityTest {
    @Test fun validAndInvalidModIdentifiers() {
        assertEquals("12345", NexusProviderIntegrity.positiveId(12345))
        assertEquals("2", NexusProviderIntegrity.positiveId(" 2 "))
        for (bad in listOf(null, 0, -1, 0L, 2147483648L, "", "0", "0002", "-1",
            "1?tab=files", "3/../", "1.2", 1.5, true, "2147483648")) {
            assertNull("invalid id: $bad", NexusProviderIntegrity.positiveId(bad))
        }
    }

    @Test fun providerCountIsNotSilentlyGuessed() {
        assertEquals(0, NexusProviderIntegrity.totalCount(0))
        assertEquals(51, NexusProviderIntegrity.totalCount(51L))
        for (bad in listOf(null, -1, -1L, Int.MAX_VALUE.toLong() + 1, "0", 2.2, true)) {
            assertNull("non-integer count: $bad", NexusProviderIntegrity.totalCount(bad))
        }
    }

    @Test fun rawPaginationRemainsProviderOwned() {
        assertTrue(NexusProviderIntegrity.hasMore(0, 50, 101))
        assertTrue(NexusProviderIntegrity.hasMore(50, 50, 101))
        assertFalse(NexusProviderIntegrity.hasMore(100, 1, 101))
        assertFalse(NexusProviderIntegrity.hasMore(0, 0, 0))
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectProviderReturningMoreThanRequestedPage() {
        NexusProviderIntegrity.hasMore(0, 51, 100)
    }

    @Test fun absentFileCategoryIsNotCalledMain() {
        assertEquals("UNSPECIFIED", NexusProviderIntegrity.fileCategory(null, false))
        assertEquals("UNSPECIFIED", NexusProviderIntegrity.fileCategory("null", false))
        assertEquals("UNSPECIFIED", NexusProviderIntegrity.fileCategory(" ", false))
        assertEquals("MAIN", NexusProviderIntegrity.fileCategory(null, true))
        assertEquals("MAIN", NexusProviderIntegrity.fileCategory("MAIN", false))
        assertEquals("OLD_VERSION", NexusProviderIntegrity.fileCategory(" old_version ", false))
        assertEquals("REMOVED", NexusProviderIntegrity.fileCategory("REMOVED", false))
    }

    @Test fun graphqlUpdatedAtAcceptsIso8601AndRejectsBadProviderDates() {
        assertEquals(1700000000000L,
            NexusProviderIntegrity.graphqlUpdatedAt("2023-11-14T22:13:20Z"))
        assertEquals(1700000000123L,
            NexusProviderIntegrity.graphqlUpdatedAt("2023-11-14T22:13:20.123Z"))
        for (value in listOf(null, "", "null", "1700000000", "not-a-date",
            "1999-12-31T23:59:59Z", "2101-01-01T00:00:00Z",
            "<script>evil()</script>", "x".repeat(500))) {
            assertEquals("provider date must be unknown: $value", 0L,
                NexusProviderIntegrity.graphqlUpdatedAt(value))
        }
    }

    @Test fun timestampsRequirePlausibleEpochSeconds() {
        assertEquals(1700000000000L, NexusProviderIntegrity.epochSecondsToMillis(1700000000L))
        assertEquals(0L, NexusProviderIntegrity.epochSecondsToMillis(0))
        assertEquals(0L, NexusProviderIntegrity.epochSecondsToMillis(-1))
        assertEquals(0L, NexusProviderIntegrity.epochSecondsToMillis(Long.MAX_VALUE))
    }
}
