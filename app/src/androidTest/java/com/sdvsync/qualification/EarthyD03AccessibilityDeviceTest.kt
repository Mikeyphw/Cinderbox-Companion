package com.sdvsync.qualification

import android.content.Context
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.assertIsNotSelected
import androidx.compose.ui.test.hasProgressBarRangeInfo
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.R
import com.sdvsync.ui.components.BottomTab
import com.sdvsync.ui.components.PixelProgressBar
import com.sdvsync.ui.components.StardewBottomBar
import com.sdvsync.ui.components.StardewButton
import com.sdvsync.ui.components.StardewCard
import com.sdvsync.ui.theme.AppearanceStyle
import com.sdvsync.ui.theme.SdvSyncTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic, offline-only 320dp + enlarged-font accessibility/screenshot checks.
 * No Steam identity, save files, installed game, network access or release qualification.
 */
@RunWith(AndroidJUnit4::class)
class EarthyD03AccessibilityDeviceTest {
    @get:Rule val rule = createComposeRule()

    @Test fun bottomTabsHaveSelectedSemanticsAndCanChangeSelection() {
        var active by mutableStateOf(BottomTab.SAVES)
        rule.setContent {
            SdvSyncTheme(darkTheme = false, style = AppearanceStyle.EARTHY) {
                StardewBottomBar(selectedTab = active, onTabSelected = { active = it })
            }
        }
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val saves = context.getString(R.string.tab_saves)
        val settings = context.getString(R.string.tab_settings)
        rule.onNodeWithText(saves).assertIsSelected()
        rule.onNodeWithText(settings).assertIsNotSelected().performClick()
        rule.onNodeWithText(settings).assertIsSelected()
        rule.runOnIdle { assertEquals(BottomTab.SETTINGS, active) }
    }

    @Test fun progressBarExposesBoundedRangeForTalkBack() {
        rule.setContent {
            SdvSyncTheme(darkTheme = true, style = AppearanceStyle.EARTHY) {
                PixelProgressBar(progress = 0.65f)
            }
        }
        rule.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo(0.65f, 0f..1f)))
            .assertExists()
    }

    @Test fun daylightScreenshotAt320DpAnd160PercentFont() = captureSyntheticPreview(false, "light")

    @Test fun nighttimeScreenshotAt320DpAnd160PercentFont() = captureSyntheticPreview(true, "dark")

    private fun captureSyntheticPreview(dark: Boolean, variant: String) {
        rule.setContent {
            // Logical 320dp viewport independent of device width; enlarged text checks reflow.
            CompositionLocalProvider(LocalDensity provides Density(2f, fontScale = 1.6f)) {
                SdvSyncTheme(darkTheme = dark, style = AppearanceStyle.EARTHY) {
                    Surface(Modifier.width(320.dp).testTag("ui-d03-preview")) {
                        Column {
                            StardewCard { Text("Synthetic offline Earthy $variant preview") }
                            Spacer(Modifier.height(12.dp))
                            StardewButton(onClick = {}) { Text("Accessible action") }
                            Spacer(Modifier.height(12.dp))
                            PixelProgressBar(progress = 0.65f)
                            StardewBottomBar(BottomTab.SAVES, onTabSelected = {})
                        }
                    }
                }
            }
        }
        rule.onNodeWithText("Accessible action").assertIsDisplayed()
        val bitmap = rule.onNodeWithTag("ui-d03-preview").captureToImage().asAndroidBitmap()
        assertTrue(bitmap.width >= 320)
        assertTrue(bitmap.height > 100)
        // Private debug-test fixture, never a user screen. Pull only this known filename with run-as.
        val target = InstrumentationRegistry.getInstrumentation().targetContext
        val filename = "cinderbox-ui-d03-earthy-$variant-320dp-fs160.png"
        target.openFileOutput(filename, Context.MODE_PRIVATE).use { output ->
            assertTrue(bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, output))
        }
    }
}
