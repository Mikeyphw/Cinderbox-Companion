package com.sdvsync.qualification

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.ui.screens.ApprovedMoreContent
import com.sdvsync.ui.viewmodels.SettingsState
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic offline-only fixture. No real credentials, files or elevated access. */
@RunWith(AndroidJUnit4::class)
class UX06MoreDeviceTest {
    @get:Rule val rule = createComposeRule()

    @Test fun offlineMoreRetainsRealStatusSemanticsAndExplicitActions() {
        var connect = 0
        var settings = 0
        val fixture = SettingsState(
            isLoggedIn = false,
            hasNexusApiKey = true,  // fixture only: saved key, not proof of authorization
            shizukuInstalled = false,
            shizukuRunning = false,
            shizukuPermissionGranted = false,
            hasRoot = false
        )
        rule.setContent {
            ApprovedMoreContent(
                state = fixture,
                onConnectSteam = { connect++ },
                onOpenSettings = { settings++ },
                onOpenOperationCenter = {},
                onOpenInstallationHealth = {},
                onOpenHelp = {},
                onOpenAbout = {}
            )
        }
        rule.onNodeWithTag("cinderbox.screen.more").assertExists()
        rule.onNodeWithText("Not connected · Local mode").assertExists()
        rule.onNodeWithText("Dark · default").assertExists()
        rule.onNodeWithText("Key saved").assertExists()
        // Capture the initial approved header/card viewport, not the scrolled test position.
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 640 && bitmap.height >= 1200)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("ux06-more-synthetic.png", Context.MODE_PRIVATE).use { output ->
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output))
        }
        rule.onNodeWithTag("cinderbox.more.root").performScrollTo().assertExists()
        rule.onNodeWithTag("cinderbox.more.root").performClick()
        assertTrue("Root row may only navigate to settings", settings == 1)
        rule.onNodeWithTag("cinderbox.more.steam-action").performScrollTo().performClick()
        assertTrue("Steam connection is explicit", connect == 1)
        rule.onNodeWithTag("cinderbox.more.help").performScrollTo().assertExists()
    }
}
