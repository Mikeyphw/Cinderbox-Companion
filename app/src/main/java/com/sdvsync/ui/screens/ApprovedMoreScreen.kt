package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sdvsync.BuildConfig
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.SettingsState
import com.sdvsync.ui.viewmodels.SettingsViewModel
import org.koin.androidx.compose.koinViewModel

/** UX-06 local-first settings landing. All sensitive actions live in explicit secondary routes. */
@Composable
fun ApprovedMoreScreen(
    onConnectSteam: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenOperationCenter: () -> Unit,
    onOpenInstallationHealth: () -> Unit,
    onOpenHelp: () -> Unit,
    onOpenAbout: () -> Unit,
    viewModel: SettingsViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsState()
    // Read current settings and provider status. This UI never requests elevated permissions.
    LaunchedEffect(viewModel) { viewModel.load() }
    ApprovedMoreContent(
        state = state,
        onConnectSteam = onConnectSteam,
        onOpenSettings = onOpenSettings,
        onOpenOperationCenter = onOpenOperationCenter,
        onOpenInstallationHealth = onOpenInstallationHealth,
        onOpenHelp = onOpenHelp,
        onOpenAbout = onOpenAbout
    )
}

@Composable
private fun MoreSection(name: String) {
    Text(name, color = Dark.Ink,
        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
        modifier = Modifier.padding(top = 10.dp, bottom = 2.dp).semantics { heading() })
}

@Composable
private fun MoreStatus(label: String, emphasized: Boolean = false) {
    Surface(color = if (emphasized) Dark.Mint else Dark.Paper2,
        shape = RoundedCornerShape(50)) {
        Text(label, color = if (emphasized) Dark.Forest else Dark.Muted,
            style = MaterialTheme.typography.labelSmall,
            maxLines = 2, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp))
    }
}

@Composable
private fun MoreActionRow(
    icon: ImageVector,
    title: String,
    description: String,
    status: String? = null,
    positive: Boolean = false,
    tag: String,
    onClick: () -> Unit
) {
    Row(Modifier.fillMaxWidth().testTag(tag)
        .clickable(role = Role.Button, onClick = onClick)
        .padding(horizontal = 12.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Surface(shape = RoundedCornerShape(11.dp), color = Dark.Paper2) {
            Icon(icon, contentDescription = null, tint = Dark.Forest,
                modifier = Modifier.padding(10.dp).size(20.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                color = Dark.Ink)
            Text(description, style = MaterialTheme.typography.bodySmall, color = Dark.Muted)
        }
        if (status != null) {
            Box(Modifier.widthIn(max = 108.dp)) { MoreStatus(status, positive) }
        } else {
            Icon(Icons.Outlined.ChevronRight, contentDescription = null,
                tint = Dark.Faint, modifier = Modifier.size(18.dp))
        }
    }
    HorizontalDivider(color = Dark.Line, thickness = 1.dp)
}

@Composable
fun ApprovedMoreContent(
    state: SettingsState,
    onConnectSteam: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenOperationCenter: () -> Unit,
    onOpenInstallationHealth: () -> Unit,
    onOpenHelp: () -> Unit,
    onOpenAbout: () -> Unit
) {
    Column(Modifier.fillMaxSize().testTag("cinderbox.screen.more")
        .background(Dark.Background).verticalScroll(rememberScrollState())
        .padding(horizontal = 17.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) {
                Text("MAKE IT YOURS", color = Dark.Forest,
                    style = MaterialTheme.typography.labelSmall.copy(letterSpacing = 1.sp))
                Text("More", color = Dark.Ink,
                    style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.semantics { heading() })
                Text("Connections, preferences and support.", color = Dark.Muted,
                    style = MaterialTheme.typography.bodyMedium)
            }
            IconButton(onClick = onOpenAbout, modifier = Modifier.testTag("cinderbox.more.about")) {
                Icon(Icons.Outlined.Info, contentDescription = "About Cinderbox", tint = Dark.Ink)
            }
        }

        Surface(color = Dark.Paper, shape = RoundedCornerShape(18.dp),
            border = BorderStroke(1.dp, Dark.Line),
            modifier = Modifier.fillMaxWidth().testTag("cinderbox.more.steam")) {
            Column(Modifier.background(Brush.linearGradient(listOf(Dark.Paper, Dark.Paper2)))
                .padding(15.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(11.dp)) {
                    Icon(Icons.Outlined.Cloud, contentDescription = null, tint = Dark.Forest,
                        modifier = Modifier.size(26.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Steam account", color = Dark.Ink,
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
                        Text(if (state.isLoggedIn) "Connected · Steam account" else "Not connected · Local mode",
                            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                    }
                    MoreStatus(if (state.isLoggedIn) "Connected" else "Optional", state.isLoggedIn)
                }
                Text("Steam is never required to open Cinderbox. Game downloads and cloud saves require an authorized Steam session.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Button(onClick = if (state.isLoggedIn) onOpenSettings else onConnectSteam,
                    modifier = Modifier.fillMaxWidth().testTag("cinderbox.more.steam-action")) {
                    Text(if (state.isLoggedIn) "Manage Steam connection" else "Connect Steam")
                }
            }
        }

        MoreSection("Appearance")
        Surface(color = Dark.Paper, shape = RoundedCornerShape(15.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.fillMaxWidth().padding(14.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Color theme", color = Dark.Ink,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold))
                    Text("The approved Cinderbox appearance", color = Dark.Muted,
                        style = MaterialTheme.typography.bodySmall)
                }
                MoreStatus("Dark · default", true)
            }
        }

        MoreSection("Connections & permissions")
        Surface(color = Dark.Paper, shape = RoundedCornerShape(15.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Column {
                MoreActionRow(Icons.Outlined.Key, "Nexus Mods",
                    "API key and mod browsing authorization",
                    if (state.hasNexusApiKey) "Key saved" else "Not configured",
                    state.hasNexusApiKey, "cinderbox.more.nexus", onOpenSettings)
                MoreActionRow(Icons.Outlined.Security, "Shizuku",
                    "Optional privileged file access",
                    when {
                        !state.shizukuInstalled -> "Not installed"
                        state.shizukuRunning && state.shizukuPermissionGranted -> "Permission granted"
                        state.shizukuRunning -> "No permission"
                        else -> "Not running"
                    }, state.shizukuRunning && state.shizukuPermissionGranted,
                    "cinderbox.more.shizuku", onOpenSettings)
                MoreActionRow(Icons.Outlined.Build, "Root access",
                    "Explicit opt-in only", if (state.hasRoot) "Enabled" else "Off",
                    false, "cinderbox.more.root", onOpenSettings)
                MoreActionRow(Icons.Outlined.Folder, "File access",
                    "Storage permissions and directory selection",
                    "Configure", tag = "cinderbox.more.file-access", onClick = onOpenSettings)
            }
        }

        MoreSection("Preferences")
        Surface(color = Dark.Paper, shape = RoundedCornerShape(15.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Column {
                MoreActionRow(Icons.Outlined.Notifications, "Notifications",
                    "Download, update and recovery alerts", "Configure",
                    tag = "cinderbox.more.notifications", onClick = onOpenSettings)
                MoreActionRow(Icons.Outlined.Sync, "Automatic cloud sync",
                    "Requires Steam and separate storage authorization", "Review",
                    tag = "cinderbox.more.sync", onClick = onOpenSettings)
            }
        }

        MoreSection("Help & app")
        Surface(color = Dark.Paper, shape = RoundedCornerShape(15.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Column {
                MoreActionRow(Icons.Outlined.HelpOutline, "Help & safety",
                    "Guides and important cautions", tag = "cinderbox.more.help", onClick = onOpenHelp)
                MoreActionRow(Icons.Outlined.Dashboard, "Operation center",
                    "Downloads, transfers and recovery guidance",
                    tag = "cinderbox.more.operations", onClick = onOpenOperationCenter)
                MoreActionRow(Icons.Outlined.VerifiedUser, "Installation health",
                    "Inspect game, loader and permissions",
                    tag = "cinderbox.more.health", onClick = onOpenInstallationHealth)
                MoreActionRow(Icons.Outlined.Info, "About Cinderbox",
                    "Version and safety information", tag = "cinderbox.more.about-row", onClick = onOpenAbout)
                MoreActionRow(Icons.Outlined.Tune, "Advanced settings",
                    "Accounts, storage access and existing controls",
                    tag = "cinderbox.more.advanced", onClick = onOpenSettings)
            }
        }
        Text("Local saves and mods remain available without Steam. Permissions are requested only from explicit settings actions.",
            color = Dark.Faint, style = MaterialTheme.typography.bodySmall)
    }
}

/** Lightweight UX-06 deep destinations; full support/help flows remain later UX milestones. */
@Composable
fun ApprovedMoreInfoScreen(topic: String, onBack: () -> Unit) {
    val about = topic == "about"
    Column(Modifier.fillMaxSize().background(Dark.Background)
        .testTag(if (about) "cinderbox.screen.more-about" else "cinderbox.screen.more-help")
        .verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(13.dp)) {
        TextButton(onClick = onBack) { Text("‹ Back") }
        Text(if (about) "About Cinderbox" else "Help & safety", color = Dark.Ink,
            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.semantics { heading() })
        if (about) {
            Text("Cinderbox Companion · v${BuildConfig.VERSION_NAME}", color = Dark.Muted)
            Text("The approved dark theme is fixed. Device qualification, release publication and automatic device installation remain separately gated.",
                color = Dark.Muted)
        } else {
            Text("You can browse local saves and mods without a Steam account.", color = Dark.Muted)
            Text("Steam authentication is optional. A connection does not automatically authorize game downloads or cloud synchronization.",
                color = Dark.Muted)
            Text("Nexus, Root, Shizuku and storage permissions must be configured explicitly in advanced settings. Review proposed file changes before applying them.",
                color = Dark.Muted)
            Text("Installed files and manifest dependencies are not proof of Android runtime compatibility.",
                color = Dark.Muted)
        }
    }
}
