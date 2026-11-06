package com.sdvsync.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Immutable
import androidx.compose.ui.graphics.Color

/** Approved 2026-11-06 single dark theme. Hex values are pinned to the HTML contract. */
@Immutable
object CinderboxDarkTokens {
    val Background = Color(0xFF101915)
    val Paper = Color(0xFF1B2922)
    val Paper2 = Color(0xFF22362B)
    val Paper3 = Color(0xFF2A4536)
    val Ink = Color(0xFFECF5E9)
    val Muted = Color(0xFFACBDB0)
    val Faint = Color(0xFF829B8A)
    val Line = Color(0xFF324739)
    val Forest = Color(0xFF8CD9A8)
    val Forest2 = Color(0xFF78C89A)
    val Accent = Color(0xFFEEBC78)
    val Mint = Color(0xFF274936)
    val Warn = Color(0xFFECC58A)
    val WarnBackground = Color(0xFF45341E)
    val Danger = Color(0xFFE9A198)
    val DangerBackground = Color(0xFF412824)
    val Hero = Color(0xFF173D2D)

    val colorScheme = darkColorScheme(
        primary = Forest,
        onPrimary = Background,
        primaryContainer = Mint,
        onPrimaryContainer = Ink,
        secondary = Accent,
        onSecondary = Background,
        secondaryContainer = Paper2,
        onSecondaryContainer = Ink,
        tertiary = Accent,
        onTertiary = Background,
        tertiaryContainer = WarnBackground,
        onTertiaryContainer = Warn,
        background = Background,
        onBackground = Ink,
        surface = Paper,
        onSurface = Ink,
        surfaceVariant = Paper2,
        onSurfaceVariant = Muted,
        surfaceContainerLowest = Background,
        surfaceContainerLow = Paper,
        surfaceContainer = Paper,
        surfaceContainerHigh = Paper2,
        surfaceContainerHighest = Paper3,
        outline = Line,
        outlineVariant = Line,
        error = Danger,
        onError = Background,
        errorContainer = DangerBackground,
        onErrorContainer = Danger,
        inverseSurface = Ink,
        inverseOnSurface = Background,
        inversePrimary = Forest2,
        scrim = Color.Black
    )
}
