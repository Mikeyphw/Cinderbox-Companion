package com.sdvsync.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.TextStyle
import java.util.Locale

/**
 * UX-00/01/02 native Home foundation. Mirrors the approved dark 393dp reference
 * layout, with live action routing but NO fabricated saves, mods or activity.
 * This composable does not touch game files or request privileged permissions.
 */
@Composable
fun HomeScreen(
    onOpenGame: () -> Unit,
    onOpenSaves: () -> Unit,
    onOpenMods: () -> Unit,
    onOpenMore: () -> Unit,
    onOpenInstallationHealth: () -> Unit,
    onOpenOperationCenter: () -> Unit,
    isSteamConnected: Boolean = false,
    onConnectSteam: () -> Unit = {},
    greetingOverride: String? = null,
    weekdayOverride: String? = null
) {
    var welcomeDismissed by rememberSaveable { mutableStateOf(false) }
    val hour = LocalTime.now().hour
    val greeting = greetingOverride ?: when (hour) {
        in 5..11 -> "Good morning ☀"
        in 12..17 -> "Good afternoon ☀"
        else -> "Good evening ☀"
    }
    val weekday = weekdayOverride ?: LocalDate.now()
        .dayOfWeek.getDisplayName(TextStyle.FULL, Locale.getDefault()).uppercase(Locale.getDefault())
    Column(
        modifier = Modifier.fillMaxSize().background(Dark.Background)
            .testTag("cinderbox.screen.home")
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp)
    ) {
        Spacer(Modifier.height(10.dp))
        ApprovedHomeTopBar(onOpenOperationCenter)
        Spacer(Modifier.height(20.dp))
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.SpaceBetween) {
            Column(modifier = Modifier.weight(1f)) {
                Text("$weekday · YOUR COMPANION", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp))
                Text(greeting, color = Dark.Ink,
                    style = MaterialTheme.typography.headlineMedium.copy(fontSize = 25.sp, lineHeight = 31.sp, fontWeight = FontWeight.Bold),
                    modifier = Modifier.semantics { heading() })
                Text("Your farm is looking good.", color = Dark.Muted,
                    style = MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.width(6.dp))
            Surface(shape = RoundedCornerShape(50), color = Dark.Mint) {
                Text(if (isSteamConnected) "Steam connected" else "Local mode",
                    color = Dark.Forest, modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
            }
        }
        Spacer(Modifier.height(18.dp))
        ApprovedHomeHero(onOpenMods)
        Spacer(Modifier.height(12.dp))
        if (!isSteamConnected && !welcomeDismissed) {
            Surface(color = Dark.Paper, shape = RoundedCornerShape(20.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, Dark.Line),
                modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(15.dp)) {
                    Row(verticalAlignment = Alignment.Top) {
                        Surface(color = Dark.Paper2, shape = RoundedCornerShape(12.dp)) {
                            Text("☁", color = Dark.Forest,
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp),
                                style = MaterialTheme.typography.titleLarge)
                        }
                        Spacer(Modifier.width(10.dp))
                        Column {
                            Text("Steam is optional", color = Dark.Ink,
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                            Text("Local saves and mods work now. Connect to unlock game downloads and cloud saves.",
                                color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = onConnectSteam, shape = RoundedCornerShape(11.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Dark.Mint, contentColor = Dark.Ink),
                            modifier = Modifier.testTag("cinderbox.steam.connect")) {
                            Text("Connect Steam", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold))
                        }
                        OutlinedButton(onClick = { welcomeDismissed = true },
                            shape = RoundedCornerShape(11.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Dark.Line)) {
                            Text("Not now", color = Dark.Ink, style = MaterialTheme.typography.labelMedium)
                        }
                    }
                }
            }
        } else {
            Surface(color = Dark.Paper, shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, Dark.Line)) {
                Text(if (isSteamConnected)
                    "Steam is connected. Available features still require verified entitlement and access."
                else "Using local mode. Connect Steam in More when you need it.",
                    modifier = Modifier.fillMaxWidth().padding(14.dp),
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.height(20.dp))
        HomeSectionTitle("At a glance")
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ApprovedStatCard("LOCAL SAVES", "—", "View detected local saves", onOpenSaves, Modifier.weight(1f))
            ApprovedStatCard("INSTALLED MODS", "—", "Inspect local mod library", onOpenMods, Modifier.weight(1f))
        }
        Spacer(Modifier.height(22.dp))
        HomeSectionTitle("Quick actions")
        Spacer(Modifier.height(11.dp))
        Surface(color = Dark.Paper, shape = RoundedCornerShape(19.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Dark.Line)) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 13.dp)) {
                HomeAction("▣", "Open local saves", "Farmer details, backups and history", onOpenSaves)
                HomeDivider()
                HomeAction("◇", "Installation health", "Review game and SMAPI status", onOpenInstallationHealth)
                HomeDivider()
                HomeAction("⌕", "Discover mods", "Explore available mods and updates", onOpenMods)
            }
        }
        Spacer(Modifier.height(22.dp))
        HomeSectionTitle("Recent activity", "All activity", onOpenOperationCenter)
        Spacer(Modifier.height(10.dp))
        Surface(color = Dark.Paper, shape = RoundedCornerShape(18.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Dark.Line),
            modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenOperationCenter)) {
            Column(Modifier.padding(16.dp)) {
                Text("Activity & operations", color = Dark.Ink,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                Text("Open the operation center to view recorded actions and their status.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.height(28.dp))
    }
}

@Composable
private fun ApprovedHomeTopBar(onOpenOperationCenter: () -> Unit) {
    Row(Modifier.fillMaxWidth().height(49.dp).testTag("cinderbox.shell.topbar"),
        horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Surface(color = Dark.Mint, shape = RoundedCornerShape(14.dp)) {
                Box(Modifier.size(36.dp), contentAlignment = Alignment.Center) {
                    Text("♨", color = Dark.Accent, style = MaterialTheme.typography.titleLarge)
                }
            }
            Spacer(Modifier.width(9.dp))
            Column {
                Text("Cinderbox", color = Dark.Ink,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
                Text("YOUR FARM, IN ONE PLACE", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp, letterSpacing = .3.sp))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Surface(shape = RoundedCornerShape(11.dp), color = Color.Transparent,
                modifier = Modifier.size(38.dp).clickable(onClick = onOpenOperationCenter)
                    .semantics { contentDescription = "Downloads and operations" }) {
                Box(contentAlignment = Alignment.Center) { Text("↓", color = Dark.Ink, fontSize = 22.sp) }
            }
            Surface(shape = RoundedCornerShape(11.dp), color = Color.Transparent,
                modifier = Modifier.size(38.dp).clickable(onClick = onOpenOperationCenter)
                    .semantics { contentDescription = "Notifications" }) {
                Box(contentAlignment = Alignment.Center) { Text("♧", color = Dark.Ink, fontSize = 22.sp) }
            }
        }
    }
}

@Composable
private fun ApprovedHomeHero(onOpenMods: () -> Unit) {
    Box(Modifier.fillMaxWidth().heightIn(min = 230.dp).clip(RoundedCornerShape(22.dp))
        .background(Brush.linearGradient(listOf(Dark.Hero, Color(0xFF204936))))) {
        Canvas(Modifier.matchParentSize()) {
            val w = size.width
            val ht = size.height
            drawCircle(Color(0xFF26513C), radius = w * .148f, center = Offset(w * .82f, ht * .23f))
            drawCircle(Color(0xFF315B43), radius = w * .108f, center = Offset(w * .82f, ht * .23f))
            drawCircle(Color(0xFFEFC07E), radius = w * .080f, center = Offset(w * .82f, ht * .23f))
            val hillBack = Path().apply {
                moveTo(w * .30f, ht)
                cubicTo(w * .48f, ht * .52f, w * .90f, ht * .48f, w * 1.12f, ht * .63f)
                lineTo(w, ht); close()
            }
            drawPath(hillBack, Color(0xFF30684B))
            val hillFront = Path().apply {
                moveTo(w * .86f, ht)
                cubicTo(w * .68f, ht * .66f, w * .64f, ht * .58f, w * 1.08f, ht * .57f)
                lineTo(w, ht); close()
            }
            drawPath(hillFront, Color(0xFF477F59))
            drawRect(Color(0xFF234C3A), Offset(w * .65f, ht * .66f), Size(w * .022f, ht * .17f))
            drawCircle(Color(0xFF6BA366), radius = w * .076f, center = Offset(w * .66f, ht * .62f))
            val roof = Path().apply {
                moveTo(w * .78f, ht * .68f);lineTo(w * .855f, ht * .63f)
                lineTo(w * .927f, ht * .68f);close()
            }
            drawPath(roof, Color(0xFFE4B574))
            drawRect(Color(0xFFD4A265), Offset(w * .78f, ht * .68f), Size(w * .147f, ht * .10f))
            drawRect(Color(0xFF8B6039), Offset(w * .835f, ht * .73f), Size(w * .032f, ht * .05f))
        }
        Column(Modifier.padding(18.dp).fillMaxWidth(.65f)) {
            Text("A LITTLE PEACE OF MIND", color = Color(0xFFB6D8C0),
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.25.sp))
            Spacer(Modifier.height(5.dp))
            Text("Your valley, beautifully organized.", color = Color.White,
                style = MaterialTheme.typography.headlineMedium.copy(fontSize = 25.sp, lineHeight = 27.sp, fontWeight = FontWeight.Bold),
                modifier = Modifier.semantics { heading() })
            Spacer(Modifier.height(12.dp))
            Text("Everything important, right where you need it.",
                color = Color(0xFFC6DECA), style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(14.dp))
            Button(onClick = onOpenMods, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF4D7AA), contentColor = Dark.Hero),
                shape = RoundedCornerShape(12.dp), contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 13.dp, vertical = 7.dp)) {
                Text("Explore mods", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold))
            }
        }
    }
}

@Composable
private fun HomeSectionTitle(label: String, action: String? = null, onClick: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = Dark.Ink, style = MaterialTheme.typography.titleSmall.copy(fontSize = 16.sp, fontWeight = FontWeight.Bold),
            modifier = Modifier.semantics { heading() })
        if (action != null && onClick != null) {
            Text(action, color = Dark.Forest, style = MaterialTheme.typography.labelMedium,
                modifier = Modifier.clickable(onClick = onClick))
        }
    }
}

@Composable
private fun ApprovedStatCard(title: String, count: String, desc: String,
                             onClick: () -> Unit, modifier: Modifier = Modifier) {
    Surface(modifier = modifier.heightIn(min = 99.dp).clickable(onClick = onClick),
        color = Dark.Paper, shape = RoundedCornerShape(17.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Dark.Line)) {
        Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(title, color = Dark.Muted,
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, fontSize = 10.sp))
            Text(count, color = Dark.Ink, fontSize = 25.sp, fontWeight = FontWeight.Bold)
            Text(desc, color = Dark.Muted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 10.sp))
        }
    }
}

@Composable
private fun HomeAction(icon: String, title: String, description: String, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Surface(color = Dark.Paper2, shape = RoundedCornerShape(12.dp)) {
            Box(Modifier.size(39.dp), contentAlignment = Alignment.Center) {
                Text(icon, color = Dark.Forest, fontSize = 22.sp)
            }
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = Dark.Ink, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
            Text(description, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
        }
        Text("›", color = Dark.Muted, fontSize = 22.sp)
    }
}

@Composable
private fun HomeDivider() {
    Box(Modifier.fillMaxWidth().height(1.dp).background(Dark.Line))
}
