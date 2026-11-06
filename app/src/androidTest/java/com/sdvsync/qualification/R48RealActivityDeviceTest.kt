package com.sdvsync.qualification

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.espresso.Espresso
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.ui.components.BottomTab
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * R48A: actual MainActivity and both Navigation Compose graphs on an isolated,
 * freshly provisioned GitHub emulator. No credentials, game files, mods, saves,
 * permission grants, root, live Steam session, update, install or publication.
 * This is NOT physical-device, TalkBack or real-game acceptance.
 */
@RunWith(AndroidJUnit4::class)
class R48RealActivityDeviceTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun tab(tab: BottomTab) = rule.onNode(
        hasText(InstrumentationRegistry.getInstrumentation().targetContext.getString(tab.labelRes)) and
            SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.Tab)
    )

    private fun enterOffline() {
        rule.onNodeWithText("Your valley, beautifully organized.").assertExists()
        tab(BottomTab.HOME).assertIsSelected().assertIsDisplayed()
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
    }

    /**
     * Fixed, non-user-content checkpoint values only. If a hosted test fails,
     * the collector permits only this bounded diagnostic instead of raw logs.
     */
    private fun checkpoint(test: String, phase: String) {
        require(test == "tabs" || test == "operations")
        require(phase.matches(Regex("[a-z0-9_]{1,48}")))
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("r48-checkpoint-$test.txt", Context.MODE_PRIVATE).use {
            it.write(phase.toByteArray(Charsets.US_ASCII))
        }
    }

    private fun assertAnyScreenState(vararg choices: String) {
        rule.waitUntil(10_000) {
            choices.any { label ->
                rule.onAllNodesWithText(label).fetchSemanticsNodes().isNotEmpty()
            }
        }
    }

    private fun screenshot(name: String) {
        // All captures are of real UI in a zero-account, isolated, hosted emulator.
        // Never use these helpers on user hardware or a restored/private test profile.
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 320 && bitmap.height >= 480)
        ctx.openFileOutput("r48-real-$name-320dp-fs160.png", Context.MODE_PRIVATE).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
    }

    @Test fun realOfflineFiveTabNavigationAndPrivatePreviews() {
        checkpoint("tabs", "enter_offline")
        enterOffline()
        checkpoint("tabs", "home")
        assertEquals(5, BottomTab.entries.size)
        screenshot("home")
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val areas = listOf(
            Triple(BottomTab.DOWNLOAD, "Stardew Valley", "game"),
            Triple(BottomTab.SAVES, "Your saves", "saves"),
            Triple(BottomTab.MODS, "Managing mods", "mods"),
            Triple(BottomTab.SETTINGS, "Personalize and manage", "more")
        )
        for ((dest, heading, imageName) in areas) {
            checkpoint("tabs", "select_$imageName")
            tab(dest).performClick().assertIsSelected().assertIsDisplayed()
            checkpoint("tabs", "content_$imageName")
            when (dest) {
                BottomTab.SAVES -> {
                    // A fresh offline emulator has no real saves. The guide is
                    // displayed ONLY when the save list is populated. Loading,
                    // empty and bounded error states are valid, not test failures.
                    rule.onNodeWithText(ctx.getString(com.sdvsync.R.string.dashboard_title))
                        .assertExists()
                    assertAnyScreenState(
                        heading, "Loading your saves",
                        ctx.getString(com.sdvsync.R.string.dashboard_no_saves),
                        "Saves could not be loaded"
                    )
                }
                BottomTab.MODS -> {
                    // As with Saves, the Mods guide exists only for a nonempty
                    // inventory. Test the real page's safe no-data states.
                    assertAnyScreenState(
                        heading, "Loading installed mods",
                        ctx.getString(com.sdvsync.R.string.mods_empty_title),
                        "Mods could not be loaded"
                    )
                }
                else -> rule.onNodeWithText(heading).assertExists()
            }
            checkpoint("tabs", "capture_$imageName")
            for (other in BottomTab.entries.filter { it != dest }) {
                tab(other).assertExists()
            }
            screenshot(imageName)
        }
        checkpoint("tabs", "return_home")
        tab(BottomTab.HOME).performClick().assertIsSelected().assertIsDisplayed()
        rule.onNodeWithText("Your valley, beautifully organized.").assertExists()
        checkpoint("tabs", "done")
    }

    @Test fun realHomeShortcutsAndNestedBackNavigation() {
        enterOffline()
        tab(BottomTab.DOWNLOAD).performClick()
        tab(BottomTab.DOWNLOAD).assertIsSelected()
        rule.onNodeWithText("Stardew Valley").assertExists()
        Espresso.pressBack()
        tab(BottomTab.HOME).assertIsSelected()
        rule.onNodeWithText("Your valley, beautifully organized.").assertExists()
        rule.onNodeWithText("Installation health").performScrollTo().performClick()
        rule.onNodeWithText("Read-only checks. Detection is not cryptographic integrity verification.")
            .assertExists()
        Espresso.pressBack()
        tab(BottomTab.HOME).assertIsSelected()
    }

    @Test fun realPreLoginSettingsBackRequiresNoSteam() {
        // UX-00: local settings are accessible without Steam; back returns Home.
        enterOffline()
        tab(BottomTab.SETTINGS).performClick().assertIsSelected()
        rule.onNodeWithText("Dark · default").performScrollTo().assertExists()
        tab(BottomTab.HOME).performClick().assertIsSelected()
        rule.onNodeWithText("Your valley, beautifully organized.").assertExists()
    }

    @Test fun realOperationCenterReadOnlyReturn() {
        checkpoint("operations", "enter_offline")
        enterOffline()
        checkpoint("operations", "open_center")
        rule.onNodeWithText("All activity").performScrollTo().performClick()
        checkpoint("operations", "expect_title")
        assertAnyScreenState("Live, read-only status and recovery guidance")
        checkpoint("operations", "expect_no_auto_retry")
        assertAnyScreenState(
            "No automatic retry or recovery is performed here. Status may be incomplete after Android stops the app."
        )
        checkpoint("operations", "press_back")
        Espresso.pressBack()
        // The operation center belongs to the parent NavHost. Restoration of
        // the nested MainScreen can span an animated navigation transition.
        checkpoint("operations", "expect_home")
        assertAnyScreenState("Your valley, beautifully organized.")
        checkpoint("operations", "expect_home_tab")
        tab(BottomTab.HOME).assertIsSelected()
        checkpoint("operations", "done")
    }
}
