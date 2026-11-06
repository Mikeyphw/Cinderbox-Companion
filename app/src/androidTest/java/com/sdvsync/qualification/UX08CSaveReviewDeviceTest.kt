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
import com.sdvsync.ui.screens.ApprovedSaveDeepContent
import com.sdvsync.ui.screens.SaveDeepArea
import com.sdvsync.ui.screens.SaveDeepSnapshot
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Only public synthetic farm data. Never reads a user's save or backup files. */
@RunWith(AndroidJUnit4::class)
class UX08CSaveReviewDeviceTest {
    @get:Rule val rule = createComposeRule()

    private fun capture(name: String) {
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 640 && bitmap.height >= 1100)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        context.openFileOutput("ux08c-$name-synthetic.png", Context.MODE_PRIVATE).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
    }

    @Test fun saveOverviewDoesNotSyncWithoutExplicitClick() {
        var viewed = false
        var reviews = 0
        var sync = false
        rule.setContent {
            ApprovedSaveDeepContent(SaveDeepArea.SAVE_REVIEW,
                SaveDeepSnapshot(title="Fixture Farm",loadState="Observed local state",
                    localStatus="Listed locally",cloudStatus="Not checked · Steam offline",
                    metadataStatus="Parsed metadata available",hasLocal=true,hasCloud=false),
                onBack={},onOpenViewer={ viewed=true },
                onOpenBackupReview={ reviews++ },onOpenLegacyBackups={},
                onReviewSync={ _,_ -> sync=true })
        }
        rule.onNodeWithTag("cinderbox.screen.save-review").assertExists()
        rule.onNodeWithText("Save details").assertExists()
        assertTrue(!viewed && reviews == 0 && !sync)
        capture("save")
        rule.onNodeWithTag("cinderbox.save-deep.viewer").performScrollTo().performClick()
        assertTrue(viewed && reviews == 0 && !sync)
    }

    @Test fun backupOverviewShowsOnlyEnumerationAndRequiresManagerNavigation() {
        var opened = false
        rule.setContent {
            ApprovedSaveDeepContent(SaveDeepArea.BACKUP_REVIEW,
                SaveDeepSnapshot(title="Fixture Farm",backupCount=2,
                    backupStatus="Enumerated locally, not verified for restore"),
                onBack={},onOpenViewer={},onOpenBackupReview={},
                onOpenLegacyBackups={ opened=true },onReviewSync={ _,_ -> })
        }
        rule.onNodeWithTag("cinderbox.screen.backup-review").assertExists()
        rule.onNodeWithText("Backup overview").assertExists()
        rule.onNodeWithText("2").assertExists()
        assertTrue(!opened)
        capture("backups")
        rule.onNodeWithTag("cinderbox.save-deep.backups-advanced").performScrollTo().performClick()
        assertTrue(opened)
    }

    @Test fun unknownSaveDoesNotOfferViewerOrSync() {
        rule.setContent {
            ApprovedSaveDeepContent(SaveDeepArea.SAVE_REVIEW,
                SaveDeepSnapshot(title="Selected save",loadState="Save not listed"),
                onBack={},onOpenViewer={},onOpenBackupReview={},
                onOpenLegacyBackups={},onReviewSync={ _,_ -> })
        }
        rule.onNodeWithText("Save not listed",substring=true).assertExists()
        rule.onNodeWithTag("cinderbox.save-deep.viewer").assertDoesNotExist()
        rule.onNodeWithTag("cinderbox.save-deep.sync-review").assertDoesNotExist()
        capture("unknown")
    }
}
