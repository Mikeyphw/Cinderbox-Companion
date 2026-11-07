package com.sdvsync.ui.ux

import android.content.Context
import android.os.SystemClock
import android.graphics.Bitmap
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.performScrollToNode
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

/** Host API36 only, real MainActivity, no Steam authentication or mod writes. */
@RunWith(AndroidJUnit4::class)
class UxDeviceChromeTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun capture(case: String, safeTag: String) {
        rule.waitForIdle()
        val node = rule.onNodeWithTag(safeTag).fetchSemanticsNode()
        val top = node.boundsInRoot.top
        // Physically-hosted 2x density: 24dp status bar is approximately 48 px.
        // Require an actual nonzero safe area rather than treating a screenshot as proof.
        assertTrue("UX09C02_STATUS_BAR_COLLISION:$case:$top", top >= 32f)
        val target = InstrumentationRegistry.getInstrumentation().targetContext
        val image = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        val width = image.width
        val height = image.height
        assertTrue("UX09C02_VIEWPORT_MISMATCH:$width:$height",
            (width == 786 && height == 1704) || (width == 720 && height == 1600))
        val fontScale = target.resources.configuration.fontScale
        assertTrue("UX09C02_FONT_SCALE_MISMATCH:$fontScale",
            fontScale in 0.98f..1.02f || fontScale in 1.98f..2.02f)
        val uniqueColors = HashSet<Int>()
        for (y in image.height / 4 until image.height * 3 / 4 step 31) {
            for (x in image.width / 8 until image.width * 7 / 8 step 31) {
                uniqueColors.add(image.getPixel(x, y) and 0x00ffffff)
                if (uniqueColors.size >= 10) break
            }
            if (uniqueColors.size >= 10) break
        }
        assertTrue("UX09C02_BLANK_FULL_DISPLAY:$case", uniqueColors.size >= 10)
        val suffix = if (fontScale > 1.5f) "200" else "100"
        val key = "ux09c02-$case-${width/2}-$suffix"
        target.openFileOutput("$key.png", Context.MODE_PRIVATE).use { stream ->
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, stream))
        }
        val receipt = JSONObject().put("case", case)
            .put("pixel_size", JSONArray().put(width).put(height))
            .put("font_percent", suffix.toInt())
            .put("content_top_px", top.toDouble())
            .put("real_offline_main_activity", true)
            .put("steam_auth_performed", false)
            .put("mod_install_performed", false)
            .put("physical_device_qualified", false)
            .put("interior_unique_colors", uniqueColors.size)
        target.openFileOutput("$key.json", Context.MODE_PRIVATE).use {
            it.write((receipt.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
    }

    @Test fun homeHeaderRespectsDeviceStatusBar() {
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        capture("home", "cinderbox.shell.topbar")
    }

    /**
     * A Steam session-resume transition and NavHost animations can outlive
     * Compose's immediate idle signal, especially after a 200% font change.
     * Await the SAME required semantics (never skip or assume authentication).
     * Named failures keep hosted logs useful without exposing form values.
     */
    private fun requireStage(stage: String, assertion: () -> Unit) {
        val deadline = SystemClock.uptimeMillis() + 12_000L
        var lastFailure: AssertionError? = null
        do {
            rule.waitForIdle()
            try {
                assertion()
                println("UX09C02_STAGE_PASS:" + stage)
                return
            } catch (failure: AssertionError) {
                lastFailure = failure
            }
            SystemClock.sleep(200L)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("UX09C02_STAGE_FAILED:" + stage, lastFailure)
    }

    @Test fun voluntarySteamConnectionHasClearReturnToApp() {
        requireStage("home-connect-action") {
            rule.onNodeWithTag("cinderbox.steam.connect").assertExists()
        }
        // Home is a real vertically scrolling screen. At 200% system text,
        // the optional Steam card can be below the visible viewport. Compose
        // can find its semantics node without that node being tappable.
        // Scroll the existing button into view and require actual visibility
        // BEFORE a real click; never navigate directly or fake login state.
        requireStage("home-connect-visible") {
            rule.onNodeWithTag("cinderbox.steam.connect")
                .performScrollTo()
                .assertIsDisplayed()
        }
        rule.onNodeWithTag("cinderbox.steam.connect").performClick()
        requireStage("steam-screen") {
            rule.onNodeWithTag("cinderbox.steam-login.screen").assertExists()
        }
        requireStage("steam-introduction") {
            rule.onNodeWithText("Connect your Steam account").assertExists()
        }
        // This negative contract remains strict: local mode was already active.
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        requireStage("steam-qr-action") {
            rule.onNodeWithTag("cinderbox.steam-login.qr").assertExists()
        }
        requireStage("steam-header") {
            rule.onNodeWithTag("cinderbox.steam-login.header").assertExists()
        }
        capture("steam", "cinderbox.steam-login.header")
        requireStage("steam-back-action") {
            rule.onNodeWithTag("cinderbox.steam-login.back").assertExists()
        }
        rule.onNodeWithTag("cinderbox.steam-login.back").performClick()
        requireStage("home-after-steam-back") {
            rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        }
    }

    @Test fun advancedModManagerHasResponsiveToolbarAndBack() {
        rule.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        rule.onNodeWithTag("cinderbox.screen.mods").assertExists()
        // The Advanced action belongs to a LazyColumn item. Scroll the container
        // to that item before clicking: a child-level scroll action is unsupported.
        rule.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("cinderbox.mods.advanced"))
        rule.onNodeWithTag("cinderbox.mods.advanced").performClick()
        rule.onNodeWithTag("cinderbox.screen.advanced-mods").assertExists()
        for (name in listOf("backups", "updates", "browse", "import")) {
            rule.onNodeWithTag("cinderbox.advanced-mods.action.$name").assertExists()
        }
        capture("mods", "cinderbox.advanced-mods.header")
        rule.onNodeWithTag("cinderbox.advanced-mods.back").performClick()
        rule.onNodeWithTag("cinderbox.screen.mods").assertExists()
    }
}
