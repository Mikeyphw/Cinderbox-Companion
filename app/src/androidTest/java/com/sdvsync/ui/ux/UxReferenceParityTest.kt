package com.sdvsync.ui.ux

import android.content.Context
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.espresso.Espresso
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.ui.components.BottomTab
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import androidx.compose.ui.graphics.Color
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * UX-09A: actual MainActivity and navigation on a freshly provisioned, offline
 * GitHub-hosted API36 emulator, never on private user devices. These tests assert
 * UI/navigation semantics and the pinned dark token constants. Screenshot PNGs
 * are evidence for UX-09B, NOT approval of native/browser pixel parity.
 * No physical-device qualification is claimed.
 */
@RunWith(AndroidJUnit4::class)
class UxReferenceParityTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun tab(destination: BottomTab) = rule.onNodeWithTag(destination.testTag)

    private fun offlineHome() {
        rule.onNodeWithTag("cinderbox.screen.home").assertExists()
        rule.onNodeWithText("Your valley, beautifully organized.").assertExists()
        tab(BottomTab.HOME).assertIsSelected().assertIsDisplayed()
    }

    private fun selectTab(destination: BottomTab, screenTag: String) {
        tab(destination).performClick()
        tab(destination).assertIsSelected().assertIsDisplayed()
        rule.onNodeWithTag(screenTag).assertExists()
    }

    private fun capture(label: String) {
        require(label in setOf("home", "game", "saves", "mods", "more"))
        val image = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(image.width >= 640 && image.height >= 900)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("ux09a-$label.png", Context.MODE_PRIVATE).use {
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
    }

    @Test fun darkDefaultHome() {
        offlineHome()
        rule.onNodeWithTag("cinderbox.shell.content").assertExists()
        rule.onNodeWithTag("cinderbox.shell.bottomnav").assertExists()
        capture("home")
    }

    @Test fun optionalSteamFirstLaunch() {
        offlineHome()
        rule.onNodeWithText("Local mode").assertExists()
        rule.onNodeWithText("Continue offline").assertDoesNotExist()
        rule.onNodeWithTag("cinderbox.steam.connection-status").assertExists()
        // Never click Connect Steam: auth is a separately reviewed opt-in flow.
    }

    @Test fun offlineLocalSavesRemainAvailable() {
        offlineHome()
        selectTab(BottomTab.SAVES, "cinderbox.screen.saves")
        rule.onNodeWithText("My saves").assertExists()
        rule.onNodeWithText("Local saves are always available").assertExists()
        rule.onNodeWithText("Cloud · Locked").assertExists()
        capture("saves")
    }

    @Test fun steamDownloadsLockedWithoutAuthentication() {
        offlineHome()
        selectTab(BottomTab.DOWNLOAD, "cinderbox.screen.game")
        rule.onNodeWithTag("cinderbox.game.download-action").assertExists()
        rule.onNodeWithText("Connect Steam to download").assertExists()
        rule.onNodeWithText("Review download requirements").assertDoesNotExist()
        capture("game")
    }

    @Test fun steamCloudLockedWithoutAuthentication() {
        offlineHome()
        selectTab(BottomTab.SAVES, "cinderbox.screen.saves")
        rule.onNodeWithTag("cinderbox.saves.cloud-pane").assertExists()
        rule.onNodeWithText("Cloud · Locked").performClick()
        rule.onNodeWithText("Cloud saves are optional").assertExists()
        rule.onNodeWithText("Connect Steam").assertExists()
        // No sync or cloud fetch is authorized by clicking the locked pane.
    }

    @Test fun modsDiscoverAndSections() {
        offlineHome()
        selectTab(BottomTab.MODS, "cinderbox.screen.mods")
        val labels = listOf("discover", "installed", "updates", "profiles")
        labels.forEach { key ->
            rule.onNodeWithTag("cinderbox.mods.section.$key").performClick().assertIsSelected()
            rule.onNodeWithTag("cinderbox.mods.$key", useUnmergedTree = true).assertExists()
            rule.onNodeWithTag("cinderbox.screen.mods").assertExists()
        }
        capture("mods")
    }

    @Test fun allFiveBottomTabs() {
        offlineHome()
        assertEquals(5, BottomTab.entries.size)
        val routeScreens = listOf(
            BottomTab.HOME to "cinderbox.screen.home",
            BottomTab.DOWNLOAD to "cinderbox.screen.game",
            BottomTab.SAVES to "cinderbox.screen.saves",
            BottomTab.MODS to "cinderbox.screen.mods",
            BottomTab.SETTINGS to "cinderbox.screen.more"
        )
        for ((destination, screen) in routeScreens) {
            selectTab(destination, screen)
            for (other in BottomTab.entries) tab(other).assertExists()
        }
        capture("more")
        selectTab(BottomTab.HOME, "cinderbox.screen.home")
    }

    @Test fun darkThemeTokenParity() {
        offlineHome()
        // Exact approved token constants, not proof of cross-renderer pixel parity.
        assertEquals(Color(0xFF101915), Dark.Background)
        assertEquals(Color(0xFF1B2922), Dark.Paper)
        assertEquals(Color(0xFF22362B), Dark.Paper2)
        assertEquals(Color(0xFFECF5E9), Dark.Ink)
        assertEquals(Color(0xFF8CD9A8), Dark.Forest)
        assertEquals(Color(0xFFEEBC78), Dark.Accent)
        assertEquals(Dark.Background, Dark.colorScheme.background)
        assertEquals(Dark.Ink, Dark.colorScheme.onBackground)
        assertEquals(Dark.Forest, Dark.colorScheme.primary)
    }

    @Test fun backNavigationAndSheets() {
        offlineHome()
        selectTab(BottomTab.MODS, "cinderbox.screen.mods")
        rule.onNodeWithTag("cinderbox.mods.filter").performScrollTo().performClick()
        rule.onNodeWithText("Refine discovery").assertExists()
        rule.onNodeWithText("Show results").performScrollTo().performClick()
        rule.onNodeWithText("Refine discovery").assertDoesNotExist()
        selectTab(BottomTab.SETTINGS, "cinderbox.screen.more")
        rule.onNodeWithTag("cinderbox.more.help").performScrollTo().performClick()
        rule.onNodeWithTag("cinderbox.screen.more-help").assertExists()
        Espresso.pressBack()
        // Return to the original More tab; no redirected login or hidden write.
        rule.onNodeWithTag("cinderbox.screen.more").assertExists()
        tab(BottomTab.SETTINGS).assertIsSelected()
    }
}
