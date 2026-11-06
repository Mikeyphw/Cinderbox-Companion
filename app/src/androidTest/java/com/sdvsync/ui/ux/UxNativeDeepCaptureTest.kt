package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.ui.components.BottomTab
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * UX-09B2: four *real*, read-only deep destinations, not fake connected Steam
 * or an invented mod catalogue. Each test has a fresh actual MainActivity.
 * Runs only on a freshly provisioned, network-disabled hosted emulator.
 */
@RunWith(AndroidJUnit4::class)
class UxNativeDeepCaptureTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun openTab(tab: BottomTab) {
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        rule.onNodeWithTag(tab.testTag).performClick()
        rule.waitForIdle()
    }

    private fun capture(caseId: String, tag: String?) {
        require(caseId in setOf("download-queue", "file-access", "operation-center", "installation-health"))
        if (tag != null) rule.onNodeWithTag(tag).assertExists()
        rule.waitForIdle()
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width == 786 && bitmap.height == 1704)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("ux09b2-$caseId.png", Context.MODE_PRIVATE).use { output ->
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output))
        }
        val evidence = JSONObject()
            .put("case", caseId)
            .put("capture_px", JSONArray().put(bitmap.width).put(bitmap.height))
            .put("actual_activity", true)
            .put("offline", true)
            .put("route_asserted", true)
            .put("matched_screen_tag", tag ?: JSONObject.NULL)
            .put("credential_or_entitlement_fixture", false)
        ctx.openFileOutput("ux09b2-$caseId.json", Context.MODE_PRIVATE).use { output ->
            output.write((evidence.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
    }

    @Test fun captureDownloadQueueReadOnly() {
        openTab(BottomTab.MODS)
        rule.onNodeWithTag("cinderbox.screen.mods").assertExists()
        rule.onNodeWithTag("cinderbox.mods.download-queue").performScrollTo().performClick()
        capture("download-queue", "cinderbox.screen.download-queue")
    }

    @Test fun captureFileAccessReadOnly() {
        openTab(BottomTab.SETTINGS)
        rule.onNodeWithTag("cinderbox.screen.more").assertExists()
        rule.onNodeWithTag("cinderbox.more.file-access").performScrollTo().performClick()
        capture("file-access", "cinderbox.screen.file-access")
    }

    @Test fun captureOperationCenterReadOnly() {
        openTab(BottomTab.SETTINGS)
        rule.onNodeWithTag("cinderbox.more.operations").performScrollTo().performClick()
        rule.onNodeWithText("Live, read-only status and recovery guidance").assertExists()
        capture("operation-center", null)
    }

    @Test fun captureInstallationHealthReadOnly() {
        openTab(BottomTab.SETTINGS)
        rule.onNodeWithTag("cinderbox.more.health").performScrollTo().performClick()
        rule.onNodeWithText("Read-only checks. Detection is not cryptographic integrity verification.").assertExists()
        capture("installation-health", null)
    }
}
