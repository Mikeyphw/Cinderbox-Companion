package com.sdvsync.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.unit.dp
import com.sdvsync.ui.theme.SdvSyncThemeExtras

@Composable
fun StardewCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    val earthy = SdvSyncThemeExtras.isEarthy
    val cardModifier = modifier
        .fillMaxWidth()
        .pixelBorder()
        .padding(8.dp) // inner padding matching the 4-layer border width

    Surface(
        modifier = if (onClick != null) {
            cardModifier.clickable(onClick = onClick)
        } else {
            cardModifier
        },
        shape = RectangleShape,
        color = if (earthy) MaterialTheme.colorScheme.surfaceContainerLow else MaterialTheme.colorScheme.surfaceContainerHigh
    ) {
        Column { content() }
    }
}
