package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.DashboardViewModel
import com.sdvsync.ui.viewmodels.SaveEntry
import org.koin.androidx.compose.koinViewModel

/**
 * UX-04: local-first Saves. Displays only data supplied by DashboardViewModel.
 * No filesystem path, write authorization, automatic sync or fake farm inventory.
 * The existing Dashboard and detail/backup/sync workflows remain available.
 */
@Composable
fun ApprovedSavesScreen(
    isSteamConnected: Boolean,
    onConnectSteam: () -> Unit,
    onOpenSave: (String) -> Unit,
    onOpenBackups: (String) -> Unit,
    onOpenSyncDetail: (String, Boolean, Boolean) -> Unit,
    onOpenSyncHistory: () -> Unit,
    onOpenAdvancedSaves: () -> Unit,
    onOpenSaveReview: (String) -> Unit = {},
    viewModel: DashboardViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsState()
    var cloudSelected by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(viewModel) { viewModel.refresh() }
    val visible = state.saves.filter { if (cloudSelected) it.hasCloud else it.hasLocal }

    LazyColumn(
        modifier = Modifier.fillMaxSize().background(Dark.Background)
            .testTag("cinderbox.screen.saves"),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(
            start = 18.dp, end = 18.dp, top = 18.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Column {
                Text("THE STORIES YOU'VE GROWN", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold, letterSpacing = 1.1.sp))
                Spacer(Modifier.height(5.dp))
                Text("My saves", color = Dark.Ink,
                    style = MaterialTheme.typography.headlineMedium.copy(
                        fontWeight = FontWeight.Bold, fontSize = 25.sp),
                    modifier = Modifier.semantics { heading() })
                Text("Your farms, local and in the cloud.", color = Dark.Muted,
                    style = MaterialTheme.typography.bodySmall)
            }
        }
        item {
            Surface(color = Dark.Paper, shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, Dark.Line)) {
                Row(Modifier.fillMaxWidth().padding(5.dp),
                    horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    SavePaneButton("Local saves", selected = !cloudSelected,
                        modifier = Modifier.weight(1f).testTag("cinderbox.saves.local-tab")) {
                        cloudSelected = false
                    }
                    SavePaneButton(if (isSteamConnected) "Cloud saves" else "Cloud · Locked",
                        selected = cloudSelected,
                        modifier = Modifier.weight(1f).testTag("cinderbox.saves.cloud-tab")) {
                        cloudSelected = true
                    }
                }
            }
        }
        if (!cloudSelected) {
            item {
                SavesNotice(
                    title = "Local saves are always available",
                    detail = "No Steam account needed to view, back up or inspect your farms.")
            }
            item {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("${visible.size} local ${if (visible.size == 1) "farm" else "farms"}",
                        color = Dark.Ink, style = MaterialTheme.typography.titleSmall)
                    OutlinedButton(onClick = onOpenSyncHistory,
                        modifier = Modifier.testTag("cinderbox.saves.history")) {
                        Text("Sync history", color = Dark.Ink)
                    }
                }
            }
        }
        if (cloudSelected && !isSteamConnected) {
            item {
                SavesEmptyCard(
                    title = "Cloud saves are optional",
                    detail = "Connect Steam when you want to sync or view cloud saves. Your local farms are available without signing in.",
                    buttonLabel = "Connect Steam", buttonAction = onConnectSteam)
            }
        } else if (cloudSelected && state.offlineMode) {
            item {
                SavesEmptyCard("Steam Cloud unavailable",
                    "Local saves remain accessible. Signing in alone does not guarantee cloud access.",
                    "Retry cloud check", { viewModel.refresh(isUserRefresh = true) })
            }
        } else if (state.isLoading && state.saves.isEmpty()) {
            item { SavesEmptyCard("Loading your saves", "Checking available save metadata. No sync has started.") }
        } else if (state.error != null && state.saves.isEmpty()) {
            item {
                SavesEmptyCard("Could not load saves",
                    "Local save information is currently unavailable. Existing files were not changed.",
                    "Retry scan", { viewModel.refresh(isUserRefresh = true) })
            }
        } else if (visible.isEmpty()) {
            item {
                SavesEmptyCard(if (cloudSelected) "No cloud saves loaded" else "No local saves found",
                    if (cloudSelected) "No Steam Cloud saves were returned. No sync has been started."
                    else "Check local file access in More. No Steam account is required.")
            }
        } else {
            items(visible, key = { it.folderName }) { save ->
                ApprovedSaveRow(
                    save = save,
                    isCloud = cloudSelected,
                    isSteamConnected = isSteamConnected,
                    onOpenSave = { onOpenSave(save.folderName) },
                    onOpenBackups = { onOpenBackups(save.folderName) },
                    onReviewSync = { onOpenSyncDetail(save.folderName, save.hasCloud, save.hasLocal) },
                    onOpenSaveReview = { onOpenSaveReview(save.folderName) }
                )
            }
        }
        item {
            OutlinedButton(
                onClick = { if (cloudSelected) onOpenSyncHistory() else viewModel.refresh(isUserRefresh = true) },
                modifier = Modifier.fillMaxWidth().testTag("cinderbox.saves.scan")) {
                Text(if (cloudSelected) "Sync history" else "Scan local saves", color = Dark.Ink)
            }
        }
        item {
            OutlinedButton(onClick = onOpenAdvancedSaves, modifier = Modifier.fillMaxWidth()) {
                Text("Import & manage saves", color = Dark.Muted)
            }
        }
    }
}

@Composable
private fun SavePaneButton(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Surface(modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(10.dp), color = if (selected) Dark.Mint else Dark.Paper) {
        Box(Modifier.fillMaxWidth().padding(vertical = 12.dp), contentAlignment = Alignment.Center) {
            Text(label, color = if (selected) Dark.Forest else Dark.Muted,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold))
        }
    }
}

@Composable
private fun SavesNotice(title: String, detail: String) {
    Surface(color = Dark.Mint, shape = RoundedCornerShape(14.dp)) {
        Row(Modifier.fillMaxWidth().padding(13.dp), verticalAlignment = Alignment.Top) {
            Text("✓", color = Dark.Forest, style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.width(10.dp))
            Column {
                Text(title, color = Dark.Ink, style = MaterialTheme.typography.titleSmall)
                Text(detail, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun SavesEmptyCard(title: String, detail: String, buttonLabel: String? = null,
                           buttonAction: (() -> Unit)? = null) {
    Surface(color = Dark.Paper, shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Dark.Line)) {
        Column(Modifier.fillMaxWidth().padding(23.dp),
            horizontalAlignment = Alignment.CenterHorizontally) {
            Text("☁", color = Dark.Forest, style = MaterialTheme.typography.headlineMedium)
            Spacer(Modifier.height(8.dp))
            Text(title, color = Dark.Ink, style = MaterialTheme.typography.titleMedium)
            Text(detail, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            if (buttonLabel != null && buttonAction != null) {
                Spacer(Modifier.height(14.dp))
                Button(onClick = buttonAction,
                    colors = ButtonDefaults.buttonColors(containerColor = Dark.Mint, contentColor = Dark.Ink)) {
                    Text(buttonLabel)
                }
            }
        }
    }
}

@Composable
private fun ApprovedSaveRow(save: SaveEntry, isCloud: Boolean, isSteamConnected: Boolean,
                            onOpenSave: () -> Unit, onOpenBackups: () -> Unit,
                            onReviewSync: () -> Unit, onOpenSaveReview: () -> Unit) {
    val meta = if (isCloud) save.cloudMeta else save.localMeta
    val farmName = meta?.farmName?.takeIf { it.isNotBlank() } ?: save.folderName
    val farmer = meta?.farmerName?.takeIf { it.isNotBlank() } ?: "Farmer details unavailable"
    val season = when (meta?.season) {
        0 -> "Spring"
        1 -> "Summer"
        2 -> "Fall"
        3 -> "Winter"
        else -> "Season unknown"
    }
    Surface(color = Dark.Paper, shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, Dark.Line),
        modifier = Modifier.fillMaxWidth().testTag("cinderbox.saves.farm-card")) {
        Column(Modifier.fillMaxWidth().padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(44.dp).background(Dark.Mint, RoundedCornerShape(13.dp)),
                    contentAlignment = Alignment.Center) {
                    Text("♣", color = Dark.Forest, style = MaterialTheme.typography.titleLarge)
                }
                Spacer(Modifier.width(11.dp))
                Column(Modifier.weight(1f)) {
                    Text(farmName, color = Dark.Ink, style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold)
                    Text("$farmer · ${if (meta == null) "Metadata not available" else "Year ${meta.year}, $season ${meta.dayOfMonth}"}",
                        color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                }
                Text("›", color = Dark.Muted, style = MaterialTheme.typography.titleLarge)
            }
            Spacer(Modifier.height(12.dp))
            Text(if (isCloud) "Cloud copy listed · Not independently verified" else "Local save available",
                color = Dark.Muted, style = MaterialTheme.typography.labelSmall)
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp),
                verticalAlignment = Alignment.CenterVertically) {
                if (save.hasLocal) {
                    OutlinedButton(onClick = onOpenSave, modifier = Modifier.weight(1f)) {
                        Text("View farm", color = Dark.Ink, fontSize = 12.sp)
                    }
                    OutlinedButton(onClick = onOpenBackups, modifier = Modifier.weight(1f)) {
                        Text("Backups", color = Dark.Ink, fontSize = 12.sp)
                    }
                }
                if (isSteamConnected && save.hasCloud) {
                    OutlinedButton(onClick = onReviewSync, modifier = Modifier.weight(1f)) {
                        Text("Review sync", color = Dark.Ink, fontSize = 12.sp)
                    }
                }
            }
            TextButton(onClick = onOpenSaveReview,
                modifier = Modifier.fillMaxWidth().testTag("cinderbox.saves.review-detail")) {
                Text("Review save details", color = Dark.Forest)
            }
        }
    }
}
