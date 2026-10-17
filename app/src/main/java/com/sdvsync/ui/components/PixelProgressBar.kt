package com.sdvsync.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import com.sdvsync.ui.theme.GoldAmber
import com.sdvsync.ui.theme.GoldBright
import com.sdvsync.ui.theme.SdvSyncThemeExtras

@Composable
fun PixelProgressBar(progress: Float, modifier: Modifier = Modifier) {
    val borderColors = SdvSyncThemeExtras.colors
    val dark = borderColors.pixelBorderDark
    val plank = borderColors.pixelBorderPlank
    val isEarthy = SdvSyncThemeExtras.isEarthy
    val earthyFill = MaterialTheme.colorScheme.tertiary
    val earthyDither = MaterialTheme.colorScheme.tertiaryContainer

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .semantics { progressBarRangeInfo = ProgressBarRangeInfo(progress.coerceIn(0f, 1f), 0f..1f) }
            .pixelBorderThin()
            .padding(4.dp) // inside the thin border
            .height(12.dp)
    ) {
        val px = 2.dp.toPx()
        val fillWidth = size.width * progress.coerceIn(0f, 1f)

        // Dithered gold fill
        var x = 0f
        var row = 0
        while (x < fillWidth) {
            val useGold = (row + ((x / px).toInt())) % 2 == 0
            val color = if (isEarthy) {
                if (useGold) earthyFill else earthyDither
            } else {
                if (useGold) GoldBright else GoldAmber
            }
            val blockWidth = minOf(px, fillWidth - x)
            drawRect(
                color = color,
                topLeft = Offset(x, 0f),
                size = Size(blockWidth, size.height)
            )
            x += px
        }

        // Unfilled area: subtle dark background
        if (fillWidth < size.width) {
            drawRect(
                color = plank.copy(alpha = 0.3f),
                topLeft = Offset(fillWidth, 0f),
                size = Size(size.width - fillWidth, size.height)
            )
        }
    }
}
