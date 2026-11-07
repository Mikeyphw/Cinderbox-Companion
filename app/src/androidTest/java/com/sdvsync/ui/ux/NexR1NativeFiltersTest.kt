package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.ui.components.BottomTab
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** UI-only acceptance: no credentials, mod writes or privileged operations. */
@RunWith(AndroidJUnit4::class)
class NexR1NativeFiltersTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun visible(tag: String) {
        val end = SystemClock.uptimeMillis() + 12000L
        do {
            rule.waitForIdle()
            try { rule.onNodeWithTag(tag).assertIsDisplayed(); return }
            catch (_: AssertionError) { SystemClock.sleep(150) }
        } while (SystemClock.uptimeMillis() < end)
        rule.onNodeWithTag(tag).assertIsDisplayed()
    }

    private fun screen(stem: String) {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue("Default font only", ctx.resources.configuration.fontScale in 0.98f..1.02f)
        val img = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        assertTrue("Refuse unknown viewport", (img.width == 786 && img.height == 1704) ||
            (img.width == 720 && img.height == 1600))
        // Preserve the raw screenshot even when the liveness audit fails. The
        // hosted runner copies only this allowlisted path on failure.
        val path = "nex-r1-$stem-${img.width / 2}.png"
        ctx.openFileOutput(path, Context.MODE_PRIVATE).use { out ->
            assertTrue(img.compress(Bitmap.CompressFormat.PNG, 100, out))
        }
        // Dense interior sampling catches blank app content without depending
        // on the exact shade/gradient count of a normal dark-themed screen.
        val colors = HashSet<Int>()
        var backgroundPixels = 0
        var foregroundPixels = 0
        var foregroundRows = 0
        for (y in img.height / 8 until img.height * 7 / 8 step 12) {
            var rowHasForeground = false
            for (x in img.width / 8 until img.width * 7 / 8 step 12) {
                val rgb = img.getPixel(x, y) and 0x00ffffff
                colors.add(rgb)
                val red = (rgb shr 16) and 0xff
                val green = (rgb shr 8) and 0xff
                val blue = rgb and 0xff
                val luminance = (299 * red + 587 * green + 114 * blue) / 1000
                if (luminance < 90) backgroundPixels++
                if (luminance > 155) {
                    foregroundPixels++
                    rowHasForeground = true
                }
            }
            if (rowHasForeground) foregroundRows++
        }
        assertTrue("Refuse blank or flat-content capture",
            colors.size >= 8 && backgroundPixels >= 64 &&
                foregroundPixels >= 5 && foregroundRows >= 2)
        println("NEX_R1_SCREENSHOT_OK:$path")
    }

    @Test fun filterSheetRealOfflineNavigation() {
        visible(BottomTab.MODS.testTag)
        rule.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        visible("cinderbox.screen.mods")
        screen("mods")
        rule.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("cinderbox.mods.filter"))
        rule.onNodeWithTag("cinderbox.mods.filter").performClick()
        visible("nex.r1.filter.sheet")
        screen("filter")
        rule.onNodeWithTag("nex.r1.filter.apply").performScrollTo().performClick()
        visible("cinderbox.screen.mods")
    }
}
