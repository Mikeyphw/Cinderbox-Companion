package com.sdvsync.ui.screens

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.sdvsync.mods.ModDownloadRecord
import com.sdvsync.mods.models.ModDownloadState
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Offline Compose acceptance. Does not touch the real game or browser. */
@RunWith(AndroidJUnit4::class)
class CbNx02BQueueControlsUiDeviceTest {
    @get:Rule val rule = createComposeRule()

    private fun record(status: String) = ModDownloadRecord(
        id = "fixture-cbnx02b", name = "Synthetic queue file", source = "nexus",
        modId = "50535", fileId = "178239", status = status,
        received = 0L, total = 0L, createdAt = 1L, updatedAt = 2L,
        detail = "Synthetic offline state"
    )

    @Test fun queuedCardMovesAndCancelsOnlyItsOwnJob() {
        var up = 0; var down = 0; var cancelled = 0; var paused = 0
        rule.setContent { MaterialTheme {
            DownloadRecordCard(record("QUEUED"), ModDownloadState.IDLE,
                onReview = {}, onOpenMod = {}, onCancel = {}, onMoveUp = { up++ },
                onMoveDown = { down++ }, onCancelOne = { cancelled++ }, onPause = { paused++ })
        } }
        rule.onNodeWithTag("cbnx02b.queue.up").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx02b.queue.down").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx02b.queue.cancel-one").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx02b.queue.pause").performScrollTo().performClick()
        assertEquals(1, up); assertEquals(1, down)
        assertEquals(1, cancelled); assertEquals(1, paused)
    }

    @Test fun pausedCardShowsExplicitRestartAndFreshAuthorization() {
        var resumed = 0; var fresh = 0
        rule.setContent { MaterialTheme {
            DownloadRecordCard(record("PAUSED"), ModDownloadState.IDLE,
                onReview = {}, onOpenMod = {}, onCancel = {},
                onResume = { resumed++ }, onRetryExact = { fresh++ })
        } }
        rule.onNodeWithTag("cbnx02b.queue.resume").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx02b.queue.retry-exact").performScrollTo().performClick()
        assertEquals(1, resumed); assertEquals(1, fresh)
    }

    @Test fun interruptedCardCannotResumeWithoutNewNexusLink() {
        var fresh = 0
        rule.setContent { MaterialTheme {
            DownloadRecordCard(record("INTERRUPTED"), ModDownloadState.IDLE,
                onReview = {}, onOpenMod = {}, onCancel = {}, onRetryExact = { fresh++ })
        } }
        rule.onNodeWithTag("cbnx02b.queue.resume").assertDoesNotExist()
        rule.onNodeWithTag("cbnx02b.queue.retry-exact").performScrollTo().performClick()
        assertEquals(1, fresh)
    }
}
