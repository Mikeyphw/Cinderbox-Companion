package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.espresso.Espresso
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
 * UX-09C01: 200% font-scale accessibility and resilience on actual offline MainActivity.
 * Hosted API36 x86_64 disposable emulator ONLY; no Steam login, mock entitlement,
 * privileged storage, background update, live mod write, or physical-device claim.
 * The CI driver configures 393dp and 360dp viewports at density 2 and font_scale=2.
 */
@RunWith(AndroidJUnit4::class)
class UxNativeAccessibilityTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private val screens = listOf(
        Triple(BottomTab.HOME, "home", "cinderbox.screen.home"),
        Triple(BottomTab.DOWNLOAD, "game", "cinderbox.screen.game"),
        Triple(BottomTab.SAVES, "saves", "cinderbox.screen.saves"),
        Triple(BottomTab.MODS, "mods", "cinderbox.screen.mods"),
        Triple(BottomTab.SETTINGS, "more", "cinderbox.screen.more")
    )

    private fun currentSizePx(): Pair<Int, Int> {
        val b = rule.onRoot().fetchSemanticsNode().boundsInRoot
        return b.width.toInt() to b.height.toInt()
    }

    private fun assertNavigationTouchTargets(): JSONArray {
        val root = rule.onRoot().fetchSemanticsNode().boundsInRoot
        val bar = rule.onNodeWithTag("cinderbox.shell.bottomnav").fetchSemanticsNode().boundsInRoot
        assertTrue("UX09C_NAV_OFFSCREEN", bar.top >= 0 && bar.bottom <= root.bottom + 2f)
        val result = JSONArray()
        for (tab in BottomTab.entries) {
            val node = rule.onNodeWithTag(tab.testTag).fetchSemanticsNode()
            val b = node.boundsInRoot
            // 48dp x 48dp, device density pinned to 2.0 in hosted CI.
            assertTrue("UX09C_TOUCH_TARGET_TOO_SMALL:${tab.name}:${b.width}x${b.height}",
                b.width >= 96f && b.height >= 96f)
            assertTrue("UX09C_TOUCH_TARGET_OFFSCREEN:${tab.name}",
                b.left >= -1f && b.right <= root.right + 2f &&
                    b.top >= 0f && b.bottom <= root.bottom + 2f)
            result.put(JSONObject().put("tab", tab.name)
                .put("width_px", b.width.toDouble()).put("height_px", b.height.toDouble()))
        }
        return result
    }

    private fun interiorColors(image: Bitmap): Int {
        val values = HashSet<Int>()
        for (y in image.height / 4 until image.height * 3 / 4 step 23) {
            for (x in image.width / 8 until image.width * 7 / 8 step 23) {
                values.add(image.getPixel(x, y) and 0x00ffffff)
                if (values.size >= 12) return values.size
            }
        }
        return values.size
    }

    private fun capture(tab: String, expectedTag: String) {
        rule.onNodeWithTag(expectedTag).assertExists()
        rule.waitForIdle()
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val (w, h) = currentSizePx()
        assertTrue("UX09C_BAD_VIEWPORT:${w}x${h}",
            (w == 786 && h == 1704) || (w == 720 && h == 1600))
        val nav = assertNavigationTouchTargets()
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue("UX09C_CAPTURE_DIMENSION_MISMATCH", bitmap.width == w && bitmap.height == h)
        val diversity = interiorColors(bitmap)
        assertTrue("UX09C_BLANK_COMPOSE_FRAME:$tab", diversity >= 12)
        val widthDp = w / 2
        ctx.openFileOutput("ux09c-${tab}-${widthDp}.png", Context.MODE_PRIVATE).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
        val meta = JSONObject().put("tab", tab).put("screen_tag", expectedTag)
            .put("width_dp", widthDp).put("density", 2.0)
            .put("font_scale", 2.0).put("real_offline_main_activity", true)
            .put("provider_fixture", false).put("local_storage_mutated", false)
            .put("pixel_size", JSONArray().put(w).put(h))
            .put("nav_targets", nav).put("interior_unique_colors", diversity)
        ctx.openFileOutput("ux09c-${tab}-${widthDp}.json", Context.MODE_PRIVATE).use {
            it.write((meta.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
    }

    @Test fun captureFiveTabsAt200PercentFont() {
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        for ((tab, key, tag) in screens) {
            if (tab != BottomTab.HOME) rule.onNodeWithTag(tab.testTag).performClick()
            rule.onNodeWithTag(tag).assertExists()
            capture(key, tag)
        }
    }

    @Test fun largeTextPreservesSteamLockAndDeepBack() {
        rule.onNodeWithTag(BottomTab.SAVES.testTag).performClick()
        rule.onNodeWithTag("cinderbox.screen.saves").assertExists()
        rule.onNodeWithText("Cloud · Locked").performClick()
        rule.onNodeWithText("Cloud saves are optional").assertExists()
        rule.onNodeWithTag(BottomTab.DOWNLOAD.testTag).performClick()
        rule.onNodeWithText("Connect Steam to download").assertExists()
        rule.onNodeWithTag(BottomTab.SETTINGS.testTag).performClick()
        rule.onNodeWithTag("cinderbox.more.help").performScrollTo().performClick()
        rule.onNodeWithTag("cinderbox.screen.more-help").assertExists()
        Espresso.pressBack()
        rule.onNodeWithTag("cinderbox.screen.more").assertExists()
    }

    @Test fun searchImeKeepsOfflineModsAccessible() {
        rule.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        rule.onNodeWithTag("cinderbox.screen.mods").assertExists()
        rule.onNodeWithTag("cinderbox.mods.search").performScrollTo().performTextInput("test query")
        rule.onNodeWithTag("cinderbox.screen.mods").assertExists()
        rule.onNodeWithTag("cinderbox.shell.bottomnav").assertExists()
        // Do not click a remote result, grant files, or interpret provider errors as success.
    }
}
