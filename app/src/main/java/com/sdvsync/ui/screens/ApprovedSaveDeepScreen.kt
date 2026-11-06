package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.BackupListViewModel
import com.sdvsync.ui.viewmodels.DashboardViewModel
import org.koin.androidx.compose.koinViewModel

/** UX-08C. Only read state; all mutations belong to pre-existing guarded screens. */
enum class SaveDeepArea { SAVE_REVIEW, BACKUP_REVIEW }

data class SaveDeepSnapshot(
    val title: String = "Selected save",
    val loadState: String = "Pending",
    val localStatus: String = "Unknown",
    val cloudStatus: String = "Not checked",
    val metadataStatus: String = "Unverified",
    val syncStatus: String = "Not assessed",
    val hasLocal: Boolean = false,
    val hasCloud: Boolean = false,
    val backupCount: Int? = null,
    val backupStatus: String = "Not checked"
)

@Composable
fun ApprovedSaveDeepScreen(
    area: SaveDeepArea,
    saveFolderName: String,
    onBack: () -> Unit,
    onOpenViewer: () -> Unit,
    onOpenBackupReview: () -> Unit,
    onOpenLegacyBackups: () -> Unit,
    onReviewSync: (Boolean, Boolean) -> Unit,
    dashboardViewModel: DashboardViewModel = koinViewModel(),
    backupsViewModel: BackupListViewModel = koinViewModel()
) {
    val dashboard by dashboardViewModel.state.collectAsState()
    val backups by backupsViewModel.state.collectAsState()
    LaunchedEffect(area, saveFolderName) {
        if (area == SaveDeepArea.SAVE_REVIEW) dashboardViewModel.refresh()
        else backupsViewModel.loadBackups(saveFolderName)
    }
    // Stable folder name is the lookup identity. Never guess from a farm's display name.
    val save = dashboard.saves.singleOrNull { it.folderName == saveFolderName }
    val meta = save?.localMeta ?: save?.cloudMeta
    val loadState = when {
        area == SaveDeepArea.BACKUP_REVIEW && backups.isLoading -> "Checking local backups"
        area == SaveDeepArea.BACKUP_REVIEW && backups.error != null -> "Backup inventory unavailable"
        area == SaveDeepArea.SAVE_REVIEW && dashboard.isLoading -> "Checking save metadata"
        area == SaveDeepArea.SAVE_REVIEW && dashboard.error != null -> "Save inventory unavailable"
        area == SaveDeepArea.SAVE_REVIEW && save == null -> "Save not listed"
        else -> "Observed local state"
    }
    val snapshot = SaveDeepSnapshot(
        title = meta?.farmName?.takeIf(String::isNotBlank) ?: "Selected save",
        loadState = loadState,
        localStatus = if (save?.hasLocal == true) "Listed locally" else "Not confirmed",
        cloudStatus = when {
            dashboard.offlineMode -> "Not checked · Steam offline"
            save?.hasCloud == true -> "Listed · not verified"
            else -> "Not confirmed"
        },
        metadataStatus = if (meta != null) "Parsed metadata available" else "No parsed metadata",
        syncStatus = when {
            save == null -> "Not assessed"
            dashboard.offlineMode -> "Steam offline · no sync started"
            else -> "Available for explicit review"
        },
        hasLocal = save?.hasLocal == true,
        hasCloud = save?.hasCloud == true,
        backupCount = if (area == SaveDeepArea.BACKUP_REVIEW && !backups.isLoading && backups.error == null)
            backups.backups.size else null,
        backupStatus = when {
            backups.isLoading -> "Checking"
            backups.error != null -> "Unavailable; originals preserved"
            else -> "Enumerated locally, not verified for restore"
        }
    )
    ApprovedSaveDeepContent(area, snapshot, onBack, onOpenViewer,
        onOpenBackupReview, onOpenLegacyBackups, onReviewSync)
}

@Composable
private fun SaveDeepFinding(label: String, value: String, provenance: String) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(label, color = Dark.Muted, style = MaterialTheme.typography.labelMedium)
        Text(value, color = Dark.Ink, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold))
        Text(provenance, color = Dark.Faint, style = MaterialTheme.typography.bodySmall)
    }
    HorizontalDivider(color = Dark.Line)
}

@Composable
fun ApprovedSaveDeepContent(
    area: SaveDeepArea,
    snapshot: SaveDeepSnapshot,
    onBack: () -> Unit,
    onOpenViewer: () -> Unit,
    onOpenBackupReview: () -> Unit,
    onOpenLegacyBackups: () -> Unit,
    onReviewSync: (Boolean, Boolean) -> Unit
) {
    val isSave = area == SaveDeepArea.SAVE_REVIEW
    Column(Modifier.fillMaxSize().background(Dark.Background)
        .testTag(if (isSave) "cinderbox.screen.save-review" else "cinderbox.screen.backup-review")
        .verticalScroll(rememberScrollState())
        .padding(horizontal = 18.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(13.dp)) {
        TextButton(onClick = onBack, modifier = Modifier.testTag("cinderbox.save-deep.back")) {
            Text("‹ Back", color = Dark.Forest)
        }
        Text(if (isSave) "YOUR FARM" else "LOCAL BACKUPS",
            color = Dark.Forest, style = MaterialTheme.typography.labelSmall)
        Text(if (isSave) "Save details" else "Backup overview", color = Dark.Ink,
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.semantics { heading() })
        Text("${snapshot.title} · ${snapshot.loadState}",
            color = Dark.Muted, style = MaterialTheme.typography.bodyMedium)
        Text(if (isSave)
            "Local and cloud listings are observations. Opening this page does not sync or edit your farm."
            else "Backup inventory is read-only here. Listed snapshots are not proof that a restore will succeed.",
            color = Dark.Muted, style = MaterialTheme.typography.bodyMedium)
        Surface(color = Dark.Paper, shape = RoundedCornerShape(18.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Column {
                if (isSave) {
                    SaveDeepFinding("Local save", snapshot.localStatus,
                        "From the current local save inventory, not filesystem integrity proof")
                    SaveDeepFinding("Steam Cloud", snapshot.cloudStatus,
                        "Steam authorization is optional; listing is not a successful sync")
                    SaveDeepFinding("Farm metadata", snapshot.metadataStatus,
                        "Parsed fields are advisory, not an authenticated save receipt")
                    SaveDeepFinding("Sync observation", snapshot.syncStatus,
                        "No transfer begins from this overview")
                } else {
                    SaveDeepFinding("Backup entries",
                        snapshot.backupCount?.toString() ?: "Unknown",
                        "Counts only entries returned by the local backup provider")
                    SaveDeepFinding("Backup inspection", snapshot.backupStatus,
                        "No automatic restore, deletion, or permission request")
                }
            }
        }
        if (isSave) {
            if (snapshot.hasLocal) {
                Button(onClick = onOpenViewer, modifier = Modifier.fillMaxWidth()
                    .testTag("cinderbox.save-deep.viewer")) {
                    Text("View farm details")
                }
            }
            OutlinedButton(onClick = onOpenBackupReview, modifier = Modifier.fillMaxWidth()
                .testTag("cinderbox.save-deep.backup-review")) {
                Text("Review local backups")
            }
            if (snapshot.hasCloud || snapshot.hasLocal) {
                OutlinedButton(onClick = { onReviewSync(snapshot.hasCloud, snapshot.hasLocal) },
                    modifier = Modifier.fillMaxWidth().testTag("cinderbox.save-deep.sync-review")) {
                    Text("Review sync options")
                }
            }
        } else {
            OutlinedButton(onClick = onOpenLegacyBackups, modifier = Modifier.fillMaxWidth()
                .testTag("cinderbox.save-deep.backups-advanced")) {
                Text("Open existing backup manager")
            }
        }
        Text("All restore and sync decisions remain in the existing guarded workflows.",
            color = Dark.Faint, style = MaterialTheme.typography.bodySmall)
    }
}
