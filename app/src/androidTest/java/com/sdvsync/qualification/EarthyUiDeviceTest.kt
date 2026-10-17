package com.sdvsync.qualification

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.sdvsync.ui.theme.AppearanceStyle
import com.sdvsync.ui.theme.SdvSyncTheme
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic visual contract only. Never touches persisted prefs, user saves, Steam or root. */
@RunWith(AndroidJUnit4::class)
class EarthyUiDeviceTest {
    @get:Rule val rule = createComposeRule()

    @Test fun earthyLightUsesWoodlandPrimaryAndVisibleContent() {
        var foreground = Color.Unspecified
        rule.setContent {
            SdvSyncTheme(darkTheme = false, style = AppearanceStyle.EARTHY) {
                foreground = MaterialTheme.colorScheme.primary
                Text("Earthy preview")
            }
        }
        rule.onNodeWithText("Earthy preview").assertIsDisplayed()
        rule.runOnIdle { assertEquals(Color(0xFF3F5744), foreground) }
    }

    @Test fun earthyDarkIsDistinctFromDaylight() {
        var foreground = Color.Unspecified
        rule.setContent {
            SdvSyncTheme(darkTheme = true, style = AppearanceStyle.EARTHY) {
                foreground = MaterialTheme.colorScheme.primary
                Text("Night preview")
            }
        }
        rule.onNodeWithText("Night preview").assertIsDisplayed()
        rule.runOnIdle { assertEquals(Color(0xFFA8BBA0), foreground) }
    }

    @Test fun classicRemainsAnIndependentTheme() {
        var foreground = Color.Unspecified
        rule.setContent {
            SdvSyncTheme(darkTheme = false, style = AppearanceStyle.CLASSIC) {
                foreground = MaterialTheme.colorScheme.primary
                Text("Classic preview")
            }
        }
        rule.onNodeWithText("Classic preview").assertIsDisplayed()
        rule.runOnIdle { assertNotEquals(Color(0xFF3F5744), foreground) }
    }
}
