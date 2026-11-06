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
import com.sdvsync.mods.models.ModProfile
import com.sdvsync.ui.screens.*
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Explicit public synthetic fixtures; no real accounts, user profiles or filesystem access. */
@RunWith(AndroidJUnit4::class)
class UX08BDeepToolsDeviceTest {
    @get:Rule val rule = createComposeRule()
    private fun capture(name: String) {
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 640 && bitmap.height >= 1100)
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        context.openFileOutput("ux08b-$name-synthetic.png", Context.MODE_PRIVATE).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
    }

    @Test fun smapiIsAdvisoryAndReviewOnly() {
        var reviewed = false
        rule.setContent {
            ApprovedGameDeepContent(DeepGameArea.SMAPI,
                DeepGameSnapshot(smapiDiscovery="CANDIDATE UNVERIFIED",
                    storedSmapiVersion="4.1", availableSmapiVersion="4.2", smapiUpdateSuggested=true),
                onBack={}, onOpenInstallationHealth={}, onReviewAdvancedSetup={reviewed=true},
                onOpenOperations={})
        }
        rule.onNodeWithTag("cinderbox.screen.smapi-overview").assertExists()
        rule.onNodeWithText("SMAPI status").assertExists()
        rule.onNodeWithText("Review suggested").assertExists()
        capture("smapi")
        rule.onNodeWithTag("cinderbox.deep-tools.advanced").performScrollTo().performClick()
        assertTrue("Review callback should be explicit", reviewed)
    }

    @Test fun recoveryDoesNotClaimRepair() {
        rule.setContent {
            ApprovedGameDeepContent(DeepGameArea.RECOVERY,
                DeepGameSnapshot(hasRecoverableDownload=true,protectedUpdateNeedsReview=true),
                onBack={}, onOpenInstallationHealth={}, onReviewAdvancedSetup={},
                onOpenOperations={})
        }
        rule.onNodeWithTag("cinderbox.screen.recovery-overview").assertExists()
        rule.onNodeWithText("Recovery status").assertExists()
        rule.onNodeWithText("Not verified").assertExists()
        capture("recovery")
    }

    @Test fun profileShowsOnlySyntheticMetadataAndExplicitManagerAction() {
        var reviewed=false
        val synthetic = ModProfile(name="Fixture Farm",id="fixture-001",
            description="Synthetic setup for hosted UI tests",
            enabledModIds=setOf("Fixture.Mod.One","Fixture.Mod.Two"),isProtected=true)
        rule.setContent {
            ApprovedProfileDetailContent(synthetic, false, false,
                onBack={},onReviewAdvancedManager={reviewed=true})
        }
        rule.onNodeWithTag("cinderbox.screen.profile-detail").assertExists()
        rule.onNodeWithText("Fixture Farm").assertExists()
        rule.onNodeWithText("Not confirmed as current").assertExists()
        capture("profile")
        rule.onNodeWithTag("cinderbox.profile-detail.review").performScrollTo().performClick()
        assertTrue("Manager navigation must be explicit", reviewed)
    }
}
