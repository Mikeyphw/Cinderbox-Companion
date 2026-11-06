package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.junit4.createComposeRule
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

    private fun capture(caseId: String, isSteamUiPreview: Boolean) {
        require(caseId in setOf("game-steam-connected", "saves-cloud-connected", "mod-detail"))
        rule.onNodeWithTag("cinderbox.shell.bottomnav").assertExists()
        rule.waitForIdle()
        // Full display capture includes Android system bars on the isolated test Activity.
        val image = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
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
