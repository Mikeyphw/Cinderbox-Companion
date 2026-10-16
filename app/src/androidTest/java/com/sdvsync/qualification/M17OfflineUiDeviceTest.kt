package com.sdvsync.qualification

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.sdvsync.MainActivity
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * M17 real Compose UI lane. Requires an intentionally signed-out test profile:
 * no credential clearing, permission grants, sync, imports, or game-file changes.
 * Recreating Activity is NOT simulated process termination or reboot recovery.
 */
@RunWith(AndroidJUnit4::class)
class M17OfflineUiDeviceTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun settingsFromLogin() {
        // Fail closed if a signed-in session unexpectedly redirects the test.
        rule.onNodeWithText("Continue offline").assertExists()
        // Login has a scrollable form: Settings may be below the visible viewport.
        // Touch injection cannot reliably click an offscreen semantics node.
        rule.onNodeWithText("Settings").performScrollTo().performClick()
        rule.waitForIdle()
        rule.onNodeWithText("Settings").assertExists()
    }

    private fun openOperationCenter() {
        rule.onNodeWithText("View downloads, mod reviews, sync outcomes and recovery guidance")
            .performScrollTo().performClick()
        rule.waitForIdle()
        rule.onNodeWithText("Live, read-only status and recovery guidance").assertIsDisplayed()
    }

    @Test fun signedOutSettingsAreAccessibleWithoutSteamLogin() {
        settingsFromLogin()
        rule.onNodeWithText("Operation center").assertExists()
    }

    @Test fun operationCenterNavigationIsReadOnly() {
        settingsFromLogin()
        openOperationCenter()
        rule.onNodeWithText("No automatic retry or recovery is performed here. Status may be incomplete after Android stops the app.")
            .assertExists()
    }

    @Test fun activityRecreationPreservesOfflineSettingsNavigation() {
        settingsFromLogin()
        rule.activityRule.scenario.recreate()
        rule.waitForIdle()
        rule.onNodeWithText("Operation center").assertExists()
    }

    @Test fun operationCenterBackReturnsToSettingsAfterRefresh() {
        settingsFromLogin()
        openOperationCenter()
        rule.onNodeWithText("Refresh checks").performClick()
        rule.waitForIdle()
        rule.onNodeWithText("Live, read-only status and recovery guidance").assertExists()
        rule.onNodeWithText("Back").performClick()
        rule.waitForIdle()
        rule.onNodeWithText("Operation center").assertExists()
    }
}
