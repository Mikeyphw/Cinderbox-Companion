package com.sdvsync.mods.api

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class NexusModPageLinksTest {
    @Test fun modScopedRoutesAreNotInterpolatedWithoutValidation() {
        assertEquals("https://www.nexusmods.com/stardewvalley/mods/123?tab=posts",
            NexusModPageLinks.forTab("123", "posts"))
        assertEquals("https://www.nexusmods.com/stardewvalley/mods/123?tab=images",
            NexusModPageLinks.forTab("123", "images"))
        assertEquals("https://www.nexusmods.com/stardewvalley/mods/123?tab=videos",
            NexusModPageLinks.forTab("123", "videos"))
        for (modId in listOf("", "0", "-3", "1/../../", "1?tab=files", "9999999999999")) {
            assertNull(NexusModPageLinks.forTab(modId, "posts"))
        }
        assertNull(NexusModPageLinks.forTab("123", "javascript:alert(1)"))
        assertNull(NexusModPageLinks.forTab("123", "not_a_tab"))
    }

    @Test fun safeExternalLinksAcceptHttpsOnlyAndRejectPrivateEndpoints() {
        assertEquals("https://github.com/Path?x=1", NexusModPageLinks.safeExternalHttps("https://github.com/Path?x=1"))
        for (value in listOf(
            "javascript:alert(1)", "file:///sdcard/test", "intent://x", "http://example.org",
            "https://evil.invalid/", "https://localhost/x", "https://127.0.0.1/x",
            "https://10.0.0.1/x", "https://user:pass@example.com/x",
            "https://example.org:8443/x", "https://internal.local/x", "https://example.org\\n/path",
            "https://[::1]/x", "https://-bad.example.org/x", "https://example.org@127.0.0.1"
        )) assertNull(value, NexusModPageLinks.safeExternalHttps(value))
    }
}
