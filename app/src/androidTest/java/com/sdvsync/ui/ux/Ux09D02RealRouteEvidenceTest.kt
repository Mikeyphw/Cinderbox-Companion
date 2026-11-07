package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.ui.test.assertDoesNotExist
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.core.view.WindowInsetsControllerCompat
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

/** UX09D02: no user data or authentication; screenshots from real MainActivity.
 * Disposable hosted API36 emulator only. No native golden/physical device claim.
 */
@RunWith(AndroidJUnit4::class)
class Ux09D02RealRouteEvidenceTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun visible(stage: String, tag: String) {
        val deadline = SystemClock.uptimeMillis() + 12_000L
        var last: AssertionError? = null
        do {
            rule.waitForIdle()
            try {
                rule.onNodeWithTag(tag).assertIsDisplayed()
                println("UX09D02_STAGE_PASS:$stage")
                return
            } catch (error: AssertionError) {
                last = error
            }
            SystemClock.sleep(160L)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("UX09D02_STAGE_FAILED:$stage:$tag", last)
    }

    private fun capture(caseName: String, tag: String) {
        visible("$caseName-content", tag)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val font = ctx.resources.configuration.fontScale
        assertTrue("UX09D02_DEFAULT_FONT_REQUIRED:$font", font in 0.98f..1.02f)
        val requestedLightIcons = !WindowInsetsControllerCompat(
            rule.activity.window, rule.activity.window.decorView
        ).isAppearanceLightStatusBars
        assertTrue("UX09D02_STATUS_BAR_FOREGROUND:$caseName", requestedLightIcons)
        val image = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        val width = image.width
        val height = image.height
        assertTrue("UX09D02_WRONG_VIEWPORT:${width}x${height}",
            (width == 786 && height == 1704) || (width == 720 && height == 1600))
        val colors = HashSet<Int>()
        for (y in image.height / 4 until image.height * 3 / 4 step 19) {
            for (x in image.width / 8 until image.width * 7 / 8 step 19) {
                colors.add(image.getPixel(x, y) and 0x00ffffff)
            }
        }
        assertTrue("UX09D02_EMPTY_CAPTURE:$caseName:${colors.size}", colors.size >= 8)
        val stem = "ux09d02-$caseName-${width / 2}"
        ctx.openFileOutput("$stem.png", Context.MODE_PRIVATE).use { out ->
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, out))
        }
        val json = JSONObject()
            .put("case", caseName)
            .put("source", "real-offline-MainActivity")
            .put("viewport", JSONArray().put(width).put(height))
            .put("font_percent", 100)
            .put("status_icons_light_requested", requestedLightIcons)
            .put("colors", colors.size)
            .put("steam_auth_attempted", false)
            .put("privileged_write_performed", false)
            .put("physical_device_qualified", false)
            .put("native_goldens_approved", false)
        ctx.openFileOutput("$stem.json", Context.MODE_PRIVATE).use { out ->
            out.write((json.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
        println("UX09D02_CAPTURE_PASS:$caseName:${width / 2}")
    }

    @Test fun homeAndGameRealOfflineScreens() {
        capture("home", "cinderbox.screen.home")
        visible("game-tab", BottomTab.DOWNLOAD.testTag)
        rule.onNodeWithTag(BottomTab.DOWNLOAD.testTag).performClick()
        capture("game", "cinderbox.screen.game")
        rule.onNodeWithTag(BottomTab.HOME.testTag).performClick()
        visible("game-return-home", "cinderbox.screen.home")
    }

    @Test fun advancedModsRealRouteAndBack() {
        visible("mods-tab", BottomTab.MODS.testTag)
        rule.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        visible("mods-entry", "cinderbox.screen.mods")
        rule.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("cinderbox.mods.advanced"))
        visible("mods-manager-entry", "cinderbox.mods.advanced")
        rule.onNodeWithTag("cinderbox.mods.advanced").performClick()
        capture("advanced-mods", "cinderbox.screen.advanced-mods")
        visible("mods-manager-back", "cinderbox.advanced-mods.back")
        rule.onNodeWithTag("cinderbox.advanced-mods.back").performClick()
        visible("mods-return", "cinderbox.screen.mods")
    }

    @Test fun steamLoginRealOfflineScreenAndBack() {
        visible("more-tab-steam", BottomTab.SETTINGS.testTag)
        rule.onNodeWithTag(BottomTab.SETTINGS.testTag).performClick()
        visible("more-steam-entry", "cinderbox.more.steam-action")
        rule.onNodeWithTag("cinderbox.more.steam-action").performClick()
        capture("steam-login", "cinderbox.steam-login.screen")
        // Login is secondary; never offer a misleading second 'Continue offline'.
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        Espresso.pressBack()
        visible("steam-back-to-local-settings", "cinderbox.screen.more")
    }

    @Test fun operationCenterRealScreenAndBack() {
        visible("more-tab-operations", BottomTab.SETTINGS.testTag)
        rule.onNodeWithTag(BottomTab.SETTINGS.testTag).performClick()
        visible("more-activity-link", "cinderbox.shell.brand-activity")
        rule.onNodeWithTag("cinderbox.shell.brand-activity").performClick()
        capture("operation-center", "cinderbox.screen.operation-center")
        visible("operation-back-button", "cinderbox.operation-center.back")
        rule.onNodeWithTag("cinderbox.operation-center.back").performClick()
        visible("operation-back-to-more", "cinderbox.screen.more")
    }
}
