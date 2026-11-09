package com.sdvsync.ui.screens

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.sdvsync.mods.ModDownloadRecord
import com.sdvsync.mods.models.ModDownloadState
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic fixture: no Nexus requests and no access to real game Mods. */
@RunWith(AndroidJUnit4::class)
class CbNx02DownloadsUiDeviceTest {
    @get:Rule val rule = createComposeRule()

    private fun record(status: String, received: Long = 0, total: Long = 0) = ModDownloadRecord(
        id = "fixture", name = "Synthetic Stardew Mod", source = "nexus",
        modId = "50535", fileId = "178239", status = status,
        received = received, total = total, createdAt = 1, updatedAt = 2,
        detail = "Synthetic offline data"
    )

    @Test fun exactFileReviewCardOpensRealReviewRoute() {
        var reviewed = 0
        var opened = ""
        rule.setContent { MaterialTheme {
            DownloadRecordCard(record("REVIEW_REQUIRED"), ModDownloadState.IDLE,
                onReview = { reviewed++ }, onOpenMod = { opened = it }, onCancel = {})
        } }
        rule.onNodeWithText("Synthetic Stardew Mod").assertExists()
        rule.onNodeWithText("nexus · Mod 50535 · File 178239").assertExists()
        rule.onNodeWithTag("cbnx02.downloads.review-item").performClick()
        assertEquals(1, reviewed)
        rule.onNodeWithText("Mod details").performClick()
        assertEquals("50535", opened)
    }

    @Test fun backlogCardCannotApproveDifferentFile() {
        var accidentallyApproved = 0
        rule.setContent { MaterialTheme {
            DownloadRecordCard(record("REVIEW_REQUIRED"), ModDownloadState.IDLE,
                onReview = { accidentallyApproved++ }, onOpenMod = {}, onCancel = {},
                isReviewHead = false, fromNotification = true)
        } }
        rule.onNodeWithText("Waiting for earlier reviews").assertExists()
        rule.onNodeWithText("Opened from notification").assertExists()
        rule.onNodeWithTag("cbnx02.downloads.review-item").assertDoesNotExist()
        assertEquals(0, accidentallyApproved)
    }

    @Test fun activeCardShowsBytesAndExplicitCancelAllAction() {
        var cancellations = 0
        rule.setContent { MaterialTheme {
            DownloadRecordCard(record("DOWNLOADING", 4096, 8192), ModDownloadState.DOWNLOADING,
                onReview = {}, onOpenMod = {}, onCancel = { cancellations++ })
        } }
        rule.onNodeWithText("4 / 8 KiB").assertExists()
        rule.onNodeWithText("Cancel all transfers").performClick()
        assertEquals(1, cancellations)
    }
}
