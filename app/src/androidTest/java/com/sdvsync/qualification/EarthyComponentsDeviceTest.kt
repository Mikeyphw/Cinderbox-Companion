package com.sdvsync.qualification

import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.sdvsync.ui.components.StardewCard
import com.sdvsync.ui.components.StardewDialog
import com.sdvsync.ui.theme.AppearanceStyle
import com.sdvsync.ui.theme.SdvSyncTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** In-memory, synthetic Compose samples only. No real account, files, or device mutation. */
@RunWith(AndroidJUnit4::class)
class EarthyComponentsDeviceTest {
    @get:Rule val rule = createComposeRule()

    @Test fun earthyCardTextVisibleInDaylight() {
        rule.setContent {
            SdvSyncTheme(darkTheme = false, style = AppearanceStyle.EARTHY) {
                StardewCard { Text("Earthy day card") }
            }
        }
        rule.onNodeWithText("Earthy day card").assertIsDisplayed()
    }

    @Test fun earthyDialogAccessibleInDarkMode() {
        rule.setContent {
            SdvSyncTheme(darkTheme = true, style = AppearanceStyle.EARTHY) {
                StardewDialog(
                    onDismissRequest = {},
                    title = "Earthy information",
                    text = "No file operations are performed",
                    confirmButton = { TextButton(onClick = {}) { Text("Close") } }
                )
            }
        }
        rule.onNodeWithText("Earthy information").assertIsDisplayed()
        rule.onNodeWithText("No file operations are performed").assertIsDisplayed()
    }

    @Test fun classicCardStillRenders() {
        rule.setContent {
            SdvSyncTheme(darkTheme = false, style = AppearanceStyle.CLASSIC) {
                StardewCard { Text("Classic card preserved") }
            }
        }
        rule.onNodeWithText("Classic card preserved").assertIsDisplayed()
    }
}
