package com.sdvsync.ui.theme

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.sdvsync.ui.components.StardewButton
import com.sdvsync.ui.components.StardewButtonVariant
import com.sdvsync.ui.components.StardewCard

/** Synthetic UI previews only: no Steam state, usernames, file paths or saved-game data. */
@Preview(name = "Earthy • daylight", showBackground = true)
@Composable
private fun EarthyDaylightPreview() = EarthySample(darkTheme = false)

@Preview(name = "Earthy • nighttime", showBackground = true)
@Composable
private fun EarthyNighttimePreview() = EarthySample(darkTheme = true)

@Composable
private fun EarthySample(darkTheme: Boolean) {
    SdvSyncTheme(style = AppearanceStyle.EARTHY, darkTheme = darkTheme) {
        androidx.compose.material3.Surface(color = MaterialTheme.colorScheme.background) {
            Column(Modifier.padding(20.dp)) {
                Text("Cinderbox Companion", style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(16.dp))
                StardewCard {
                    Column(Modifier.padding(12.dp)) {
                        Text("Your woodland workspace", style = MaterialTheme.typography.titleLarge)
                        Text("Preview content is entirely synthetic.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Spacer(Modifier.height(16.dp))
                StardewButton(onClick = {}) { Text("Open saves") }
                Spacer(Modifier.height(8.dp))
                StardewButton(onClick = {}, variant = StardewButtonVariant.Gold) { Text("Review changes") }
            }
        }
    }
}
