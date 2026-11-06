package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.mods.ModRequirementsAssessor
import com.sdvsync.mods.models.RemoteMod
import com.sdvsync.ui.components.BottomTab
import com.sdvsync.ui.components.StardewBottomBar
import com.sdvsync.ui.screens.ApprovedGameScreen
import com.sdvsync.ui.screens.ApprovedModDetailContent
import com.sdvsync.ui.screens.ApprovedSavesScreen
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.theme.SdvSyncTheme
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * UX-09B3 presentation fixtures. These are NOT a logged-in MainActivity,
 * real Steam authentication, real cloud access, provider data, or entitlement.
 * No production account/session, privileges, filesystem, or network is modified.
 */
@RunWith(AndroidJUnit4::class)
class UxNativeFixtureCaptureTest {
    @get:Rule val rule = createComposeRule()

    @Composable
    private fun FixtureMainShell(tab: BottomTab, content: @Composable () -> Unit) {
        Column(Modifier.fillMaxSize().background(Dark.Background)) {
            Box(Modifier.weight(1f).testTag("cinderbox.shell.content")) { content() }
            StardewBottomBar(selectedTab = tab, onTabSelected = {})
        }
    }

    /** Test-only frame liveness check; blank backgrounds must not count as captured UI. */
    private fun sampledInteriorColors(bitmap: Bitmap): Int {
        val colors = HashSet<Int>()
        val left = bitmap.width / 8
        val right = bitmap.width * 7 / 8
        val top = bitmap.height / 4
        val bottom = bitmap.height * 3 / 4
        for (y in top until bottom step 23) {
            for (x in left until right step 23) {
                colors.add(bitmap.getPixel(x, y) and 0x00ffffff)
                if (colors.size >= 12) return colors.size
            }
        }
        return colors.size
    }

    private fun capture(caseId: String, isSteamUiPreview: Boolean) {
        require(caseId in setOf("game-steam-connected", "saves-cloud-connected", "mod-detail"))
        rule.onNodeWithTag("cinderbox.shell.bottomnav").assertExists()
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        // Compose semantics can be present before the frame reaches Android's
        // Surface/RenderThread. Force native Compose rendering, then check pixels.
        var rootDiversity = 0
        for (attempt in 1..10) {
            rule.waitForIdle()
            rootDiversity = sampledInteriorColors(rule.onRoot().captureToImage().asAndroidBitmap())
            if (rootDiversity >= 12) break
            SystemClock.sleep(250)
        }
        assertTrue("UX09B3_COMPOSE_ROOT_BLANK:$caseId", rootDiversity >= 12)

        // Full-display evidence must come from Android, with intact system bars.
        // Never write a visually blank screenshot just because semantics passed.
        var validatedImage: Bitmap? = null
        var successfulAttempt = 0
        var displayDiversity = 0
        for (attempt in 1..12) {
            rule.waitForIdle()
            instrumentation.waitForIdleSync()
            val candidate = instrumentation.uiAutomation.takeScreenshot()
            if (candidate != null && candidate.width == 786 && candidate.height == 1704) {
                displayDiversity = sampledInteriorColors(candidate)
                if (displayDiversity >= 12) {
                    validatedImage = candidate
                    successfulAttempt = attempt
                    break
                }
            }
            candidate?.recycle()
            SystemClock.sleep(300)
        }
        val image = checkNotNull(validatedImage) { "UX09B3_BLANK_DISPLAY_CAPTURE:$caseId" }
        assertTrue(image.width == 786 && image.height == 1704)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        context.openFileOutput("ux09b3-$caseId.png", Context.MODE_PRIVATE).use { out ->
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, out))
        }
        val metadata = JSONObject()
            .put("case", caseId)
            .put("capture_px", JSONArray().put(image.width).put(image.height))
            .put("isolated_compose_fixture", true)
            .put("actual_main_activity_route", false)
            .put("steam_ui_boolean_preview", isSteamUiPreview)
            .put("real_steam_authentication", false)
            .put("real_steam_entitlement", false)
            .put("real_cloud_access", false)
            .put("provider_catalog_verified", false)
            .put("production_state_mutated", false)
            .put("display_content_nonblank", true)
            .put("display_sampled_unique_colors", displayDiversity)
            .put("display_capture_attempt", successfulAttempt)
            .put("capture_method", "android-ui-automation-full-display")
        context.openFileOutput("ux09b3-$caseId.json", Context.MODE_PRIVATE).use { out ->
            out.write((metadata.toString(2) + "\n").toByteArray(Charsets.UTF_8))
        }
    }

    @Test fun captureGameSteamConnectedUiPreview() {
        // TRUE is a presentation parameter only. The Steam service is still OFFLINE.
        rule.setContent {
            SdvSyncTheme {
                FixtureMainShell(BottomTab.DOWNLOAD) {
                    ApprovedGameScreen(
                        isSteamConnected = true,
                        onConnectSteam = {},
                        onOpenInstallationHealth = {},
                        onOpenGameSetup = {},
                        onOpenOperationCenter = {}
                    )
                }
            }
        }
        rule.onNodeWithTag("cinderbox.screen.game").assertExists()
        rule.onNodeWithText("Review download requirements").assertExists()
        capture("game-steam-connected", isSteamUiPreview = true)
    }

    @Test fun captureSavesCloudConnectedUiPreviewWithoutCloudAccess() {
        // The visible tab is presentational. DashboardViewModel still reports OFFLINE.
        rule.setContent {
            SdvSyncTheme {
                FixtureMainShell(BottomTab.SAVES) {
                    ApprovedSavesScreen(
                        isSteamConnected = true,
                        onConnectSteam = {},
                        onOpenSave = {},
                        onOpenBackups = {},
                        onOpenSyncDetail = { _, _, _ -> },
                        onOpenSyncHistory = {},
                        onOpenAdvancedSaves = {}
                    )
                }
            }
        }
        rule.onNodeWithTag("cinderbox.screen.saves").assertExists()
        rule.onNodeWithTag("cinderbox.saves.cloud-tab").performClick()
        rule.onNodeWithText("Cloud saves").assertExists()
        capture("saves-cloud-connected", isSteamUiPreview = true)
    }

    @Test fun captureModDetailWithInMemoryCatalogExample() {
        val fixture = RemoteMod(
            sourceId = "ux09b3-test-only", modId = "fixture-001",
            name = "Example Mod", author = "Test fixture",
            summary = "Deterministic presentation-only example. Not a real provider listing.",
            version = "1.0.0", categoryName = "Visual test",
            pictureUrl = null, endorsements = 14, downloads = 420
        )
        rule.setContent {
            SdvSyncTheme {
                ApprovedModDetailContent(
                    mod = fixture, files = emptyList(),
                    requirements = ModRequirementsAssessor.assess(fixture, null),
                    fileError = null, saved = false,
                    onBack = {}, onReviewFiles = {}, onSelectTab = {}, onToggleSaved = {}
                )
            }
        }
        rule.onNodeWithTag("cinderbox.screen.mod-detail").assertExists()
        rule.onNodeWithText("Example Mod").assertExists()
        capture("mod-detail", isSteamUiPreview = false)
    }
}
