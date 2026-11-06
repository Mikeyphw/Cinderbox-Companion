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
 * UX-09B evidence only. Runs on a fresh, network-disabled hosted emulator.
 * No mocked account entitlement, filesystem mutation, native golden approval,
 * physical-device acceptance, or claim of 24-case visual parity is made.
 * Captures distinct MODS sub-sections BEFORE navigating to the next section.
 */
@RunWith(AndroidJUnit4::class)
class UxNativeFidelityCaptureTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun navigate(destination: BottomTab, screen: String) {
        rule.onNodeWithTag(destination.testTag).performClick()
        rule.onNodeWithTag(screen).assertExists()
        rule.waitForIdle()
    }

    private fun capture(case: String) {
        require(case in setOf(
            "home", "game-local", "saves-local", "saves-cloud-locked",
            "mods-discover", "mods-installed", "mods-updates", "mods-profiles", "more"
        ))
        rule.waitForIdle()
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 640 && bitmap.height >= 900)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        context.openFileOutput("ux09b-$case.png", Context.MODE_PRIVATE).use { stream ->
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream))
        }
        val report = JSONObject().put("case", case)
            .put("capture_px", JSONArray().put(bitmap.width).put(bitmap.height))
            .put("bounds", JSONArray())
        val tags = listOf(
            "cinderbox.shell.content", "cinderbox.shell.bottomnav",
            "cinderbox.shell.topbar", "cinderbox.screen.home",
            "cinderbox.screen.game", "cinderbox.screen.saves",
            "cinderbox.screen.mods", "cinderbox.screen.more",
            "cinderbox.mods.discover", "cinderbox.mods.installed",
            "cinderbox.mods.updates", "cinderbox.mods.profiles"
        )
        val bounds = report.getJSONArray("bounds")
        for (tag in tags) {
            // A missing tag is recorded as missing, not fabricated as a match.
            val node = runCatching { rule.onNodeWithTag(tag).fetchSemanticsNode() }.getOrNull()
                ?: continue
            val b = node.boundsInRoot
            bounds.put(JSONObject().put("tag", tag).put("rect_px", JSONArray()
                .put(b.left.toDouble()).put(b.top.toDouble())
                .put(b.right.toDouble()).put(b.bottom.toDouble())))
        }
        context.openFileOutput("ux09b-$case.json", Context.MODE_PRIVATE).use { stream ->
            stream.write((report.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
    }

    @Test fun captureOfflineReferenceMatrix() {
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        capture("home")
        navigate(BottomTab.DOWNLOAD, "cinderbox.screen.game")
        capture("game-local")
        navigate(BottomTab.SAVES, "cinderbox.screen.saves")
        capture("saves-local")
        rule.onNodeWithText("Cloud · Locked").performClick()
        rule.onNodeWithText("Cloud saves are optional").assertExists()
        capture("saves-cloud-locked")
        navigate(BottomTab.MODS, "cinderbox.screen.mods")
        for (section in listOf("discover", "installed", "updates", "profiles")) {
            rule.onNodeWithTag("cinderbox.mods.section.$section").performClick()
            rule.onNodeWithTag("cinderbox.mods.$section", useUnmergedTree = true).assertExists()
            capture("mods-$section")
        }
        navigate(BottomTab.SETTINGS, "cinderbox.screen.more")
        capture("more")
    }
}
