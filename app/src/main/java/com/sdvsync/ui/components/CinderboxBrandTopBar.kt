package com.sdvsync.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark

/** Primary-tab header: one identical, globally meaningful action on every tab.
 * No misleading destination-specific glyphs, no duplicate queue/history shortcuts.
 * Home and Game retain their existing brand bars and read-only Activity routing.
 */
@Composable
fun CinderboxBrandTopBar(
    subtitle: String,
    onOpenOperationCenter: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth().height(49.dp)
            .testTag("cinderbox.shell.branded-topbar"),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(36.dp).clip(RoundedCornerShape(13.dp))
                .background(Dark.Mint), contentAlignment = Alignment.Center) {
                Text("♨", color = Dark.Accent, fontSize = 22.sp)
            }
            Spacer(Modifier.width(9.dp))
            Column {
                Text("Cinderbox", color = Dark.Ink,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                Text(subtitle, color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp))
            }
        }
        TextButton(
            onClick = onOpenOperationCenter,
            modifier = Modifier.heightIn(min = 48.dp)
                .testTag("cinderbox.shell.brand-activity")
                .semantics { contentDescription = "Activity and operations" }
        ) {
            Text("Activity", color = Dark.Forest,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold))
        }
    }
}
