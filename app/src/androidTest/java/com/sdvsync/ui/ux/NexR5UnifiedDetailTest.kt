package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import android.text.Spanned
import android.text.style.URLSpan
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.mods.ModRequirementsAssessor
import com.sdvsync.mods.models.RemoteMod
import com.sdvsync.mods.models.RemoteModFile
import com.sdvsync.ui.components.safeNexusSpanned
import com.sdvsync.ui.screens.ApprovedModDetailContent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic Compose fixtures on a real hosted Android 36 emulator; NOT live Nexus. */
@RunWith(AndroidJUnit4::class)
class NexR5UnifiedDetailTest {
    @get:Rule val rule = createComposeRule()

    private val mod = RemoteMod(
        sourceId = "nexus", modId = "1303", name = "NEX-R5 Native Fixture",
        author = "Synthetic Author", summary = "A summary",
        description = "<p><b>Rich description</b> and <a href=\"https://github.com\">safe link</a></p>",
        version = "2.1", categoryName = "Gameplay", pictureUrl = null,
        downloads = 100, endorsements = 12, lastUpdated = 1700000000L
    )
    private val file = RemoteModFile(
        fileId = "77", fileName = "mod-77.zip", fileVersion = "2.1",
        fileSize = 2048L, isPrimary = true, categoryName = "MAIN",
        uploadedAt = 1700000000L,
        description = "<b>Install notes</b> with formatting",
        changelogHtml = "<i>Changed content</i>"
    )

    private fun capture(stage: String) {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue("font 100%", ctx.resources.configuration.fontScale in 0.98f..1.02f)
        val img = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        assertTrue("pinned emulator size", (img.width == 786 && img.height == 1704) ||
            (img.width == 720 && img.height == 1600))
        ctx.openFileOutput("nex-r5-$stage-${img.width / 2}.png", Context.MODE_PRIVATE).use { out ->
            assertTrue(img.compress(Bitmap.CompressFormat.PNG, 100, out))
        }
    }

    @Test fun oneNativeOverviewShowsFormattedTextFilesAndExternalCommunity() {
        var downloads = 0
        var selected = ""
        var opened = ""
        rule.setContent {
            ApprovedModDetailContent(mod, listOf(file), ModRequirementsAssessor.assess(mod, null),
                null, false, {}, {}, {}, {},
                onDownloadForReview = { selected = it; downloads++ },
                onOpenExternal = { opened = it })
        }
        rule.onNodeWithTag("cinderbox.screen.mod-detail").assertExists()
        rule.onNodeWithTag("nex.r2.detail.description").assertExists()
        capture("overview")
        rule.onNodeWithTag("cinderbox.mod-detail.list")
            .performScrollToNode(hasTestTag("nex.r5.download-for-review"))
        rule.onNodeWithTag("nex.r5.download-for-review").performClick()
        assertEquals("77", selected)
        assertEquals(1, downloads)
        rule.onNodeWithTag("cinderbox.mod-detail.files").assertExists()
        capture("files")
        rule.onNodeWithTag("cinderbox.mod-detail.list")
            .performScrollToNode(hasTestTag("nex.r5.open-posts"))
        rule.onNodeWithTag("nex.r5.open-posts").performClick()
        assertEquals("https://www.nexusmods.com/stardewvalley/mods/1303?tab=posts", opened)
        rule.onNodeWithTag("cinderbox.mod-detail.list")
            .performScrollToNode(hasTestTag("nex.r5.images"))
        rule.onNodeWithTag("nex.r5.images").performClick()
        assertEquals("https://www.nexusmods.com/stardewvalley/mods/1303?tab=images", opened)
        capture("community")
        assertEquals("Read-only navigation never downloads", 1, downloads)
    }

    @Test fun requestInFlightDisablesDuplicateDownloadTap() {
        var attempts = 0
        rule.setContent {
            ApprovedModDetailContent(mod, listOf(file), ModRequirementsAssessor.assess(mod, null),
                null, false, {}, {}, {}, {}, requestInFlight = true,
                onDownloadForReview = { attempts++ })
        }
        rule.onNodeWithTag("cinderbox.mod-detail.list")
            .performScrollToNode(hasTestTag("nex.r5.download-for-review"))
        rule.onNodeWithTag("nex.r5.download-for-review").assertIsNotEnabled()
        assertEquals(0, attempts)
    }

    @Test fun formattedHtmlRemovesExecutableMarkupAndUnsafeUrlSpans() {
        val spanned = safeNexusSpanned(
            "<b>Bold</b><script>alert('X')</script>" +
            "<a href='javascript:alert(1)'>bad</a>" +
            "<a href='file:///sdcard/data'>file</a>" +
            "<a href='https://github.com/test'>good</a>"
        ) as Spanned
        assertFalse(spanned.toString().contains("alert('X')"))
        assertTrue(spanned.toString().contains("Bold"))
        val links = spanned.getSpans(0, spanned.length, URLSpan::class.java)
        assertEquals(1, links.size)
        assertEquals("https://github.com/test", links.single().url)
    }
}
