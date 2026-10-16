package com.sdvsync.qualification

import android.content.Context
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.security.MessageDigest

/**
 * M18 explicit two-stage process recovery, orchestrated by the host runner.
 * NEVER force-stop from instrumentation: that would kill the test runner itself.
 * Only writes/removes one random test marker. No save/mod/download/Steam access.
 * Activity recreation alone is not accepted as process-death evidence.
 */
@RunWith(AndroidJUnit4::class)
class M18ProcessRecoveryDeviceTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun marker(): Pair<android.content.SharedPreferences, String> {
        val nonce = InstrumentationRegistry.getArguments().getString("m18_nonce") ?: ""
        require(Regex("[0-9a-f]{32}").matches(nonce)) { "M18_NONCE_INVALID" }
        val hash = MessageDigest.getInstance("SHA-256")
            .digest(nonce.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }.take(24)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        return context.getSharedPreferences("cinderbox_m18_test_only", Context.MODE_PRIVATE) to "marker_$hash"
    }

    @Test fun seedIsolatedRecoveryMarker() {
        // Same signed-out real Activity verified by M17, but this is an M18-only stage.
        rule.onNodeWithText("Continue offline").assertExists()
        val (prefs, key) = marker()
        assertFalse("Fresh test marker must not preexist", prefs.contains(key))
        assertTrue("Test marker must be durably committed", prefs.edit().putString(key, "M18_PREPARED").commit())
    }

    @Test fun verifyMarkerAfterColdRelaunchAndClean() {
        rule.onNodeWithText("Continue offline").assertExists()
        val (prefs, key) = marker()
        try {
            assertEquals("M18_PREPARED", prefs.getString(key, null))
        } finally {
            // Remove ONLY the random key from the M18-specific preferences file.
            assertTrue("Marker cleanup must commit", prefs.edit().remove(key).commit())
        }
    }
}
