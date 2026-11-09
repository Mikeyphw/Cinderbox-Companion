package com.sdvsync.mods.api

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class CbNx01HandoffTest {
    @Test fun selectedModAndFileRemainInBrowserHandoff() {
        assertEquals(
            "https://www.nexusmods.com/stardewvalley/mods/123?tab=files&cinderbox_file=456&cinderbox_mode=nxm&cinderbox_request=sample-request-0001",
            NexusBrowserHandoff.createUrl("123", "456", "sample-request-0001")
        )
        for (bad in listOf("", "0", "-1", "1/2", "3?tab=posts", "9999999999999")) {
            assertNull(NexusBrowserHandoff.createUrl(bad, "456"))
            assertNull(NexusBrowserHandoff.createUrl("123", bad))
        }
        assertNull(NexusBrowserHandoff.createUrl("123", "456", "bad&switch=1"))
    }

    @Test fun onlyValidNxmMayStartDownload() {
        val now = 1794170000L
        val good = "nxm://stardewvalley/mods/123/files/456?key=abcDEF123-_.&expires=${now + 120}"
        val parsed = NxmUriPolicy.parse(good, now)
        assertNotNull(parsed)
        assertEquals("123", parsed?.modId)
        assertEquals("456", parsed?.fileId)
        for (bad in listOf(
            good.replace("stardewvalley", "skyrim"),
            good.replace("/files/456", "/files/456/other"),
            good.replace("/mods/123", "/mods/0"),
            good.replace("nxm:", "https:"),
            good.replace("key=abcDEF123-_.", "key="),
            good.replace("&expires=", "&key=other&expires="),
            good.replace("?key=", "?notkey="),
            good.replace("${now + 120}", "${now - 10}"),
            good.replace("${now + 120}", "${now + 8L * 24L * 3600L}"),
            "$good#trailing"
        )) assertNull(bad, NxmUriPolicy.parse(bad, now))
    }
    @Test fun iceravenIsExplicitPreferredBrowserCandidate() {
        assertEquals("io.github.forkmaintainers.iceraven",
            NexusBrowserLauncher.compatibleBrowserPackages.first())
        assertEquals(true,
            NexusBrowserLauncher.compatibleBrowserPackages.contains("org.mozilla.firefox"))
    }
}
