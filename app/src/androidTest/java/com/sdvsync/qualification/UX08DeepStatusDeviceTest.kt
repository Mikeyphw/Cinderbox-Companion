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
import com.sdvsync.ui.screens.ApprovedDeepStatusContent
import com.sdvsync.ui.screens.DeepStatusArea
import com.sdvsync.ui.screens.DeepStatusSnapshot
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Offline public fixtures only. Never captures file names, accounts or device permissions. */
@RunWith(AndroidJUnit4::class)
class UX08DeepStatusDeviceTest {
    @get:Rule val rule = createComposeRule()

    @Test fun queueIsReadOnlyAndOperationCenterIsExplicit() {
        var operations = 0
        rule.setContent {
            ApprovedDeepStatusContent(
                area = DeepStatusArea.DOWNLOAD_QUEUE,
                state = DeepStatusSnapshot(gameTransfer = "IDLE", modTransfer = "IDLE"),
                onBack = {}, onOpenAdvancedSettings = {},
                onOpenOperations = { operations++ }, onOpenHealth = {})
        }
        rule.onNodeWithText("Download queue").assertExists()
        rule.onNodeWithText("Game transfer").assertExists()
        rule.onNodeWithTag("cinderbox.screen.download-queue").assertExists()
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 640 && bitmap.height >= 1200)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("ux08a-queue-synthetic.png", Context.MODE_PRIVATE).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
        rule.onNodeWithTag("cinderbox.deep.open-operations").performScrollTo().performClick()
        assertTrue(operations == 1)
    }

    @Test fun fileAccessNeverGrantsPermissionsImplicitly() {
        var settings = 0
        var health = 0
        rule.setContent {
            ApprovedDeepStatusContent(
                area = DeepStatusArea.FILE_ACCESS,
                state = DeepStatusSnapshot(fileStrategy = "SAF", safConfigured = true,
                    safStaging = true, shizukuInstalled = false),
                onBack = {}, onOpenAdvancedSettings = { settings++ },
                onOpenOperations = {}, onOpenHealth = { health++ })
        }
        rule.onNodeWithText("File access").assertExists()
        rule.onNodeWithText("Staging only").assertExists()
        rule.onNodeWithTag("cinderbox.screen.file-access").assertExists()
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 640 && bitmap.height >= 1200)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("ux08a-file-access-synthetic.png", Context.MODE_PRIVATE).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
        rule.onNodeWithTag("cinderbox.deep.open-settings").performScrollTo().performClick()
        assertTrue(settings == 1 && health == 0)
    }
}
