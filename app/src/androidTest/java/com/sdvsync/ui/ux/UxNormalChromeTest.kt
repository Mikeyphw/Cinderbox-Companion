package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.core.view.WindowInsetsControllerCompat
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

/** Real offline MainActivity, API36 hosted emulator, default font ONLY.
 * No authentication, privileged writes, fake data, or native-golden approval.
 */
@RunWith(AndroidJUnit4::class)
class UxNormalChromeTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    /** Do not pass a navigation step merely because an old tab has similar text.
     * Navigation animations can outlive one Compose idle cycle; still fail closed.
     */
    private fun requireVisibleTag(stage: String, tag: String) {
        val deadline = SystemClock.uptimeMillis() + 12_000L
        var last: AssertionError? = null
        do {
            rule.waitForIdle()
            try {
                rule.onNodeWithTag(tag).assertIsDisplayed()
                println("UX09D01_STAGE_PASS:$stage")
                return
            } catch (error: AssertionError) {
                last = error
            }
            SystemClock.sleep(160L)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("UX09D01_STAGE_FAILED:$stage:$tag", last)
    }

    private fun sampledColors(image: Bitmap): Int {
        val distinct = HashSet<Int>()
        for (y in image.height / 4 until image.height * 3 / 4 step 23) {
            for (x in image.width / 8 until image.width * 7 / 8 step 23) {
                distinct.add(image.getPixel(x, y) and 0x00ffffff)
            }
        }
        return distinct.size
    }

    private fun capture(case: String, screen: String) {
        requireVisibleTag("$case-screen", screen)
        requireVisibleTag("$case-brand", "cinderbox.shell.branded-topbar")
        requireVisibleTag("$case-activity", "cinderbox.shell.brand-activity")
        val top = rule.onNodeWithTag("cinderbox.shell.branded-topbar")
            .fetchSemanticsNode().boundsInRoot.top
        assertTrue("UX09D01_STATUS_OVERLAP:$case:$top", top >= 32f)
        // Appearance flag verifies Android was REQUESTED to draw light status icons;
        // pixel contrast and physical-device acceptance are separate qualifications.
        val lightIcons = !WindowInsetsControllerCompat(rule.activity.window,
            rule.activity.window.decorView).isAppearanceLightStatusBars
        assertTrue("UX09D01_DARK_STATUS_BAR_ICONS:$case", lightIcons)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val font = context.resources.configuration.fontScale
        assertTrue("UX09D01_DEFAULT_FONT_REQUIRED:$font", font in 0.98f..1.02f)
        val image = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        val width = image.width
        val height = image.height
        assertTrue("UX09D01_WRONG_SCREEN_SIZE:${width}x${height}",
            (width == 786 && height == 1704) || (width == 720 && height == 1600))
        val colors = sampledColors(image)
        assertTrue("UX09D01_BLANK_SCREEN_CONTENT:$case:$colors", colors >= 8)
        val widthDp = width / 2
        val stem = "ux09d01-$case-$widthDp"
        context.openFileOutput("$stem.png", Context.MODE_PRIVATE).use { out ->
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, out))
        }
        val data = JSONObject()
            .put("case", case)
            .put("source", "real-offline-MainActivity")
            .put("viewport", JSONArray().put(width).put(height))
            .put("brand_top_px", top.toDouble())
            .put("status_icons_light", lightIcons)
            .put("content_unique_colors", colors)
            .put("font_percent", 100)
            .put("steam_login_attempted", false)
            .put("privileged_write_performed", false)
            .put("native_golden_approved", false)
            .put("physical_device_accepted", false)
        context.openFileOutput("$stem.json", Context.MODE_PRIVATE).use { out ->
            out.write((data.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
        println("UX09D01_CAPTURE_PASS:$case:$widthDp:$colors")
    }

    /** All three primary tabs must route to the REAL operation center, then Back
     * to the originating tab. No matching an unrelated 'Operation center' text row.
     */
    private fun checkGlobalActivityAndBack(screen: String, label: String) {
        requireVisibleTag("$label-header-action", "cinderbox.shell.brand-activity")
        rule.onNodeWithTag("cinderbox.shell.brand-activity").performClick()
        requireVisibleTag("$label-operations-route", "cinderbox.screen.operation-center")
        requireVisibleTag("$label-operations-back", "cinderbox.operation-center.back")
        rule.onNodeWithTag("cinderbox.operation-center.back").performClick()
        requireVisibleTag("$label-return-to-origin", screen)
        requireVisibleTag("$label-header-restored", "cinderbox.shell.brand-activity")
    }

    @Test fun modsHeaderActivityAndQuickManagerNavigateAndReturn() {
        requireVisibleTag("mods-nav-tab", BottomTab.MODS.testTag)
        rule.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        capture("mods", "cinderbox.screen.mods")
        checkGlobalActivityAndBack("cinderbox.screen.mods", "mods")
        // The manager button is a LazyColumn item, so scroll the CONTAINER,
        // not the child. This keeps earlier HF02/HF04 fixes intact.
        rule.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("cinderbox.mods.advanced"))
        requireVisibleTag("mods-advanced-entry", "cinderbox.mods.advanced")
        rule.onNodeWithTag("cinderbox.mods.advanced").performClick()
        requireVisibleTag("mods-advanced-route", "cinderbox.screen.advanced-mods")
        requireVisibleTag("mods-advanced-back", "cinderbox.advanced-mods.back")
        rule.onNodeWithTag("cinderbox.advanced-mods.back").performClick()
        requireVisibleTag("mods-return-from-manager", "cinderbox.screen.mods")
    }

    @Test fun savesHeaderActivityNavigatesAndReturns() {
        requireVisibleTag("saves-nav-tab", BottomTab.SAVES.testTag)
        rule.onNodeWithTag(BottomTab.SAVES.testTag).performClick()
        capture("saves", "cinderbox.screen.saves")
        checkGlobalActivityAndBack("cinderbox.screen.saves", "saves")
    }

    @Test fun moreHeaderActivityNavigatesAndReturns() {
        requireVisibleTag("more-nav-tab", BottomTab.SETTINGS.testTag)
        rule.onNodeWithTag(BottomTab.SETTINGS.testTag).performClick()
        capture("more", "cinderbox.screen.more")
        checkGlobalActivityAndBack("cinderbox.screen.more", "more")
    }
}
