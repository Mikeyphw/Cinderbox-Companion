package com.sdvsync.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

/** Original, app-owned palette inspired by woodland and aged-paper materials, not mod assets. */
private val Forest = Color(0xFF3F5744)
private val Bark = Color(0xFF604B3B)
private val Clay = Color(0xFF8A5237)
private val Paper = Color(0xFFF0EAD9)
private val Surface = Color(0xFFE5DBC6)
private val Ink = Color(0xFF342C26)
private val Moss = Color(0xFFA8BBA0)
private val Night = Color(0xFF211F1B)
private val NightSurface = Color(0xFF302B25)
private val NightInk = Color(0xFFF1E7D5)

val EarthyLightColorScheme = lightColorScheme(
    primary = Forest,
    onPrimary = Color(0xFFF8F3E8),
    primaryContainer = Color(0xFFD1DEC9),
    onPrimaryContainer = Color(0xFF263A2B),
    secondary = Bark,
    onSecondary = Color(0xFFFFF2E3),
    secondaryContainer = Color(0xFFE0D1C2),
    onSecondaryContainer = Color(0xFF3C2E25),
    tertiary = Clay,
    onTertiary = Color(0xFFFFF3EA),
    tertiaryContainer = Color(0xFFEBD3C3),
    onTertiaryContainer = Color(0xFF4E2D20),
    background = Paper,
    onBackground = Ink,
    surface = Surface,
    onSurface = Ink,
    surfaceVariant = Color(0xFFD8CBB2),
    onSurfaceVariant = Color(0xFF54483E),
    surfaceContainerLowest = Color(0xFFF8F3E8),
    surfaceContainerLow = Paper,
    surfaceContainer = Surface,
    surfaceContainerHigh = Color(0xFFD8CBB2),
    surfaceContainerHighest = Color(0xFFC9B99D),
    outline = Color(0xFF766959),
    outlineVariant = Color(0xFFB6A58F),
    error = Color(0xFF9E3B37),
    onError = Color.White,
    errorContainer = Color(0xFFFFDAD5),
    onErrorContainer = Color(0xFF571C1A),
    inverseSurface = NightSurface,
    inverseOnSurface = NightInk,
    inversePrimary = Moss,
    scrim = Color.Black
)

val EarthyDarkColorScheme = darkColorScheme(
    primary = Moss,
    onPrimary = Color(0xFF1A2820),
    primaryContainer = Color(0xFF3F5744),
    onPrimaryContainer = Color(0xFFF8F3E8),
    secondary = Color(0xFFC9B49F),
    onSecondary = Color(0xFF33271F),
    secondaryContainer = Color(0xFF534235),
    onSecondaryContainer = Color(0xFFEDE1D3),
    tertiary = Color(0xFFD8AA87),
    onTertiary = Color(0xFF412719),
    tertiaryContainer = Color(0xFF60402D),
    onTertiaryContainer = Color(0xFFFFE6CE),
    background = Night,
    onBackground = NightInk,
    surface = NightSurface,
    onSurface = NightInk,
    surfaceVariant = Color(0xFF3C342C),
    onSurfaceVariant = Color(0xFFCABDAC),
    surfaceContainerLowest = Color(0xFF171612),
    surfaceContainerLow = Night,
    surfaceContainer = NightSurface,
    surfaceContainerHigh = Color(0xFF3C342C),
    surfaceContainerHighest = Color(0xFF4B4137),
    outline = Color(0xFFA29483),
    outlineVariant = Color(0xFF62584C),
    error = Color(0xFFFFB3A9),
    onError = Color(0xFF611E1B),
    errorContainer = Color(0xFF7B2824),
    onErrorContainer = Color(0xFFFFDAD5),
    inverseSurface = Surface,
    inverseOnSurface = Ink,
    inversePrimary = Forest,
    scrim = Color.Black
)
