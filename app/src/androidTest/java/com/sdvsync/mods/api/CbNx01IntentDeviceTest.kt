package com.sdvsync.mods.api

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith

/** Device-side validation; a real authenticated Firefox handoff is qualified separately. */
@RunWith(AndroidJUnit4::class)
class CbNx01IntentDeviceTest {
    @Test fun androidRuntimeRejectsOtherGamesAndExpiredNxm() {
        val now = System.currentTimeMillis() / 1000
        val correct = "nxm://stardewvalley/mods/123/files/456?key=abcdef&expires=${now + 120}"
        assertEquals("456", NxmUriPolicy.parse(correct, now)?.fileId)
        assertNull(NxmUriPolicy.parse(correct.replace("stardewvalley", "skyrim"), now))
        assertNull(NxmUriPolicy.parse(correct.replace("${now + 120}", "${now - 1}"), now))
        assertNull(NxmUriPolicy.parse(correct.replace("/files/456", "/files/789/extra"), now))
    }
}
