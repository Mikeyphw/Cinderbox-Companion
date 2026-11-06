package com.sdvsync.qualification

import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performScrollToIndex
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.mods.ModRequirementsAssessor
import com.sdvsync.mods.models.RemoteMod
import com.sdvsync.mods.models.ModManifest
import com.sdvsync.mods.models.ModDependency
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.ui.screens.ApprovedModDetailContent
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic public fixture only. No Steam, Nexus account, installed mod or user files. */
@RunWith(AndroidJUnit4::class)
class UX05DetailVisualDeviceTest {
    @get:Rule val rule = createComposeRule()

    @Test fun approvedDetailEmitsPrivateSyntheticScreenshotAndSemantics() {
        val fixture = RemoteMod(sourceId="nexus",modId="1",name="Expanded Valley",
            author="Sample Studio",summary="New places, characters and stories across the valley.",
            version="1.9",categoryName="Expansions",downloads=2400000)
        val main = InstalledMod(ModManifest("Expanded Valley","Sample Studio","1.9",
            "ExpandedValley.Mod","",dependencies=listOf(ModDependency("Framework.Mod","2.0-beta"))),
            folderName="ExpandedValley",folderPath="synthetic",enabled=true,installedFrom="nexus:1")
        val provider = InstalledMod(ModManifest("Framework","Fixture","2.0-rc",
            "Framework.Mod",""),folderName="Framework",folderPath="synthetic",enabled=true)
        val report = ModRequirementsAssessor.assess(fixture,listOf(main,provider))
        rule.setContent {
            ApprovedModDetailContent(
                fixture,emptyList(),report,null,false,
                onBack={},onReviewFiles={},onSelectTab={},onToggleSaved={})
        }
        rule.onNodeWithTag("cinderbox.screen.mod-detail").assertExists()
        rule.onNodeWithTag("cinderbox.mod-detail.cover").assertExists()
        rule.onNodeWithText("Expanded Valley").assertExists()
        val root = rule.onRoot().fetchSemanticsNode().boundsInRoot
        val cover = rule.onNodeWithTag("cinderbox.mod-detail.cover")
            .fetchSemanticsNode().boundsInRoot
        val navigation = rule.onNodeWithTag("cinderbox.shell.bottomnav")
            .fetchSemanticsNode().boundsInRoot
        assertTrue("cover should be within root", cover.left >= root.left && cover.right <= root.right)
        assertTrue("cover should precede navigation", cover.bottom < navigation.top)
        assertTrue("cover should span main content", cover.width >= root.width * 0.70f)
        assertTrue("bottom nav must be visible", navigation.bottom <= root.bottom + 1f)
        val bitmap=rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width>=640 && bitmap.height>=1200)
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val geometry = JSONObject()
            .put("root", listOf(root.left,root.top,root.width,root.height))
            .put("cover", listOf(cover.left,cover.top,cover.width,cover.height))
            .put("bottom", listOf(navigation.left,navigation.top,navigation.width,navigation.height))
            .put("hosted_synthetic_only", true)
        context.openFileOutput("ux05bd-anchors.json",0).use {
            it.write(geometry.toString().toByteArray(Charsets.UTF_8))
        }
        context.openFileOutput("ux05bd-detail-fixture.png",0).use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG,100,it))
        }
        rule.onNodeWithTag("cinderbox.mod-detail.list").performScrollToIndex(7)
        rule.onNodeWithTag("cinderbox.mod-detail.compatibility").assertExists()
    }
}
