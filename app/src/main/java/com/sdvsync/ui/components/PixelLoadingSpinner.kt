package com.sdvsync.ui.components

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.semantics
import com.sdvsync.R
import com.sdvsync.ui.theme.GoldAmber
import com.sdvsync.ui.theme.GoldBright
import com.sdvsync.ui.theme.SdvSyncThemeExtras
import androidx.compose.material3.MaterialTheme

/**
 * Animated pixel art loading spinner — a rotating gold star.
 */
@Composable
fun PixelLoadingSpinner(modifier: Modifier = Modifier, size: Dp = 32.dp) {
    val earthy = SdvSyncThemeExtras.isEarthy
    val loadingStatus = stringResource(R.string.ui_loading_status)
    val infiniteTransition = rememberInfiniteTransition(label = "spinner")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200),
            repeatMode = RepeatMode.Restart
        ),
        label = "spinnerRotation"
    )

    PixelIcon(
        pixelData = StarIconData,
        palette = listOf(
            androidx.compose.ui.graphics.Color.Transparent,
            if (earthy) MaterialTheme.colorScheme.tertiary else GoldBright,
            if (earthy) MaterialTheme.colorScheme.secondary else GoldAmber
        ),
        modifier = modifier
            .semantics { stateDescription = loadingStatus }
            .graphicsLayer { rotationZ = rotation },
        size = size
    )
}
