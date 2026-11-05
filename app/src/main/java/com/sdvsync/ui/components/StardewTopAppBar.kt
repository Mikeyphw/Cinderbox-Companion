package com.sdvsync.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.sdvsync.ui.theme.SdvSyncThemeExtras

/**
 * R48B: Real 320dp/160%-font screenshots proved that the persistent Steam badge
 * and extra action icons could completely crowd out screen titles. In compact
 * windows the title gets a dedicated app-bar row, and every existing action
 * remains visible in a wrapping, independently measured auxiliary row.
 *
 * This is layout only: no authentication, retry, update or storage action is
 * introduced, removed or invoked automatically.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StardewTopAppBar(title: String, navigationIcon: @Composable () -> Unit = {}, actions: @Composable () -> Unit = {}) {
    val borderColors = SdvSyncThemeExtras.colors
    val earthy = SdvSyncThemeExtras.isEarthy
    val barColor = if (earthy) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainer

    // BoxWithConstraints responds to actual window/pane width (not the physical
    // device's nominal screen width), including split-screen and large text.
    BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
        val compact = maxWidth < 420.dp
        Column(
            modifier = Modifier.fillMaxWidth().drawBehind {
                val px = 2.dp.toPx()
                val plank = borderColors.pixelBorderPlank
                val highlight = borderColors.pixelBorderHighlight
                val y = size.height - px
                var x = 0f
                var useHighlight = true
                while (x < size.width) {
                    drawRect(
                        color = if (useHighlight) highlight else plank,
                        topLeft = Offset(x, y),
                        size = Size(px, px)
                    )
                    x += px
                    useHighlight = !useHighlight
                }
            }
        ) {
            TopAppBar(
                title = {
                    Text(
                        title,
                        style = if (compact) MaterialTheme.typography.titleMedium else MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (earthy) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.primary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                },
                navigationIcon = navigationIcon,
                actions = {
                    if (!compact) {
                        Row { SteamLiveBadge(); actions() }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = barColor,
                    navigationIconContentColor = if (earthy) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.primary,
                    actionIconContentColor = if (earthy) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                )
            )

            if (compact) {
                // FlowRow keeps Import/Refresh/Backups/etc. available rather
                // than clipping them into an inaccessible overflow. The actual
                // commands remain those supplied by the owning screen.
                Surface(color = barColor) {
                    FlowRow(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        SteamLiveBadge()
                        actions()
                    }
                }
            }
        }
    }
}
