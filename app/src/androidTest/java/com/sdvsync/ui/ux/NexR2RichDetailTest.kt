package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.mods.ModRequirementsAssessor
import com.sdvsync.mods.models.RemoteMod
import com.sdvsync.mods.models.RemoteModFile
import com.sdvsync.ui.screens.ApprovedModDetailContent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Source-bounded synthetic UI fixtures, not live Nexus results or device qualification. */
@RunWith(AndroidJUnit4::class)
class NexR2RichDetailTest {
    @get:Rule val rule = createComposeRule()

    private fun mod(description: String? = "<p>Independent mod metadata</p>") = RemoteMod(
        sourceId = "nexus", modId = "12345", name = "Synthetic Provider Fixture",
        author = "Fixture Author", summary = "A read-only test fixture",
        description = description, version = "1.2.3", categoryName = "Utilities",
        pictureUrl = null, downloads = 12800, endorsements = 640,
        lastUpdated = 1700000000L
    )

    private fun file(id: String, category: String): RemoteModFile = RemoteModFile(
        fileId = id, fileName = "fixture-$id.zip", fileVersion = "1.2.3",
        fileSize = 2048L, isPrimary = category == "MAIN", categoryName = category,
        uploadedAt = 1700000000L, description = "Fixture notes"
    )

    private fun capture(label: String) {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(ctx.resources.configuration.fontScale in 0.98f..1.02f)
        val bitmap = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        assertTrue(bitmap.width == 720 || bitmap.width == 786)
        val name = "nex-r2-$label-${bitmap.width / 2}.png"
        ctx.openFileOutput(name, Context.MODE_PRIVATE).use { out ->
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, out))
        }
        println("NEX_R2_FIXTURE_CAPTURE_OK:$name")
    }

    @Test fun richDetailsShowRealFieldsAndOnlyExplicitFileReview() {
        val remote = mod("<p>Read-only description</p><script>evil()</script>")
        val files = listOf(file("1", "MAIN"), file("2", "OPTIONAL"), file("3", "OLD_VERSION"))
        var reviews = 0
        rule.setContent {
            ApprovedModDetailContent(remote, files, ModRequirementsAssessor.assess(remote, null),
                null, false, {}, { reviews++ }, {}, {})
        }
        rule.onNodeWithTag("cinderbox.screen.mod-detail").assertExists()
        rule.onNodeWithText("Synthetic Provider Fixture").assertExists()
        assertEquals(0, reviews)
        capture("overview")
        rule.onNodeWithTag("cinderbox.mod-detail.list").performScrollToNode(hasText("Main files"))
        rule.onNodeWithText("Main files").assertIsDisplayed()
        rule.onNodeWithText("Optional files").assertExists()
        rule.onNodeWithText("Old files").assertExists()
        rule.onNodeWithTag("cinderbox.mod-detail.files").performScrollTo().performClick()
        assertEquals(1, reviews)
        capture("files")
    }

    @Test fun missingDetailsNeverClaimInstallationOrCompatibility() {
        val remote = mod(null).copy(version = "", categoryName = null, pictureUrl = null)
        var reviews = 0
        rule.setContent {
            ApprovedModDetailContent(remote, emptyList(), ModRequirementsAssessor.assess(remote, null),
                "Provider unavailable", false, {}, { reviews++ }, {}, {})
        }
        rule.onNodeWithTag("cinderbox.mod-detail.list").performScrollToNode(
            hasText("Compatibility not verified"))
        rule.onNodeWithText("Compatibility not verified").assertExists()
        rule.onNodeWithTag("cinderbox.mod-detail.list").performScrollToNode(
            hasText("Provider file list unavailable."))
        rule.onNodeWithText("Provider file list unavailable.").assertExists()
        assertEquals(0, reviews)
        capture("missing")
    }
}
