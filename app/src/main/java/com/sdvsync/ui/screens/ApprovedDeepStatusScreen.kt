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
import com.sdvsync.download.GameDownloadManager
import com.sdvsync.mods.ModDownloadManager
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.SettingsViewModel
import org.koin.androidx.compose.koinViewModel
import org.koin.compose.koinInject

/** UX-08A secondary routes expose observed state only, not an authorization shortcut. */
enum class DeepStatusArea { DOWNLOAD_QUEUE, FILE_ACCESS }

data class DeepStatusSnapshot(
    val gameTransfer: String = "Unobserved",
    val modTransfer: String = "Unobserved",
    val smapiTransfer: String = "Unobserved",
    val gameReceivedBytes: Long = 0L,
    val modReceivedBytes: Long = 0L,
    val fileStrategy: String = "Unknown",
    val safConfigured: Boolean = false,
    val safStaging: Boolean = false,
    val allFilesPermission: Boolean = false,
    val allFilesUsable: Boolean = false,
    val shizukuInstalled: Boolean = false,
    val shizukuRunning: Boolean = false,
    val shizukuPermission: Boolean = false,
    val rootExplicitlyEnabled: Boolean = false
)

/** Uses exactly the same read-only sources as Operation Center and Settings. */
@Composable
fun ApprovedDeepStatusScreen(
    area: DeepStatusArea,
    onBack: () -> Unit,
    onOpenAdvancedSettings: () -> Unit,
    onOpenOperations: () -> Unit,
    onOpenHealth: () -> Unit,
    settingsViewModel: SettingsViewModel = koinViewModel()
) {
    val settings by settingsViewModel.state.collectAsState()
    val game: GameDownloadManager = koinInject()
    val mods: ModDownloadManager = koinInject()
    val gameState by game.progress.collectAsState()
    val modState by mods.progress.collectAsState()
    val smapi by game.smapiProgress.collectAsState()
    LaunchedEffect(settingsViewModel) { settingsViewModel.load() }
    ApprovedDeepStatusContent(
        area = area,
        state = DeepStatusSnapshot(
            gameTransfer = gameState.state.name,
            modTransfer = modState.state.name,
            smapiTransfer = when {
                smapi.isDownloading -> "Downloading"
                smapi.isRunning -> "Processing"
                else -> "Not currently active"
            },
            gameReceivedBytes = gameState.downloadedBytes.coerceAtLeast(0L),
            modReceivedBytes = modState.downloadedBytes.coerceAtLeast(0L),
            fileStrategy = settings.fileAccessMode,
            safConfigured = settings.safConfigured,
            safStaging = settings.safIsStaging,
            allFilesPermission = settings.allFilesPermissionGranted,
            allFilesUsable = settings.allFilesAccessWorking,
            shizukuInstalled = settings.shizukuInstalled,
            shizukuRunning = settings.shizukuRunning,
            shizukuPermission = settings.shizukuPermissionGranted,
            rootExplicitlyEnabled = settings.hasRoot
        ),
        onBack = onBack,
        onOpenAdvancedSettings = onOpenAdvancedSettings,
        onOpenOperations = onOpenOperations,
        onOpenHealth = onOpenHealth
    )
}

@Composable
private fun DeepStatusRow(label: String, observation: String, provenance: String) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically) {
            Text(label, color = Dark.Ink,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                modifier = Modifier.weight(1f))
            Text(observation, color = Dark.Forest,
                style = MaterialTheme.typography.labelSmall)
        }
        Text(provenance, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
    }
    HorizontalDivider(color = Dark.Line)
}

@Composable
fun ApprovedDeepStatusContent(
    area: DeepStatusArea,
    state: DeepStatusSnapshot,
    onBack: () -> Unit,
    onOpenAdvancedSettings: () -> Unit,
    onOpenOperations: () -> Unit,
    onOpenHealth: () -> Unit
) {
    val isQueue = area == DeepStatusArea.DOWNLOAD_QUEUE
    Column(Modifier.fillMaxSize().background(Dark.Background)
        .testTag(if (isQueue) "cinderbox.screen.download-queue" else "cinderbox.screen.file-access")
        .verticalScroll(rememberScrollState())
        .padding(horizontal = 18.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(13.dp)) {
        TextButton(onClick = onBack, modifier = Modifier.testTag("cinderbox.deep.back")) {
            Text("‹ Back", color = Dark.Forest)
        }
        Text(if (isQueue) "DOWNLOADS & TRANSFERS" else "STORAGE & PERMISSIONS",
            color = Dark.Forest, style = MaterialTheme.typography.labelSmall)
        Text(if (isQueue) "Download queue" else "File access", color = Dark.Ink,
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.semantics { heading() })
        Text(if (isQueue)
            "Current transfer observations. No unseen queued jobs or completion percentages are inferred."
            else "Review actual configured access. A granted permission is not proof of working access.",
            color = Dark.Muted, style = MaterialTheme.typography.bodyMedium)

        Surface(color = Dark.Paper, shape = RoundedCornerShape(17.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Column {
                if (isQueue) {
                    DeepStatusRow("Game transfer", state.gameTransfer,
                        "Observed download state · ${state.gameReceivedBytes} received bytes")
                    DeepStatusRow("Mod transfer", state.modTransfer,
                        "Observed download state · ${state.modReceivedBytes} received bytes")
                    DeepStatusRow("SMAPI work", state.smapiTransfer,
                        "Live setup activity, not a verified installation receipt")
                } else {
                    DeepStatusRow("Selected access strategy", state.fileStrategy,
                        "Existing Settings provider; device access may change")
                    DeepStatusRow("Storage Access Framework",
                        when {
                            state.safStaging -> "Staging only"
                            state.safConfigured -> "Configured"
                            else -> "Not configured"
                        }, "Configured directory status, not general filesystem authorization")
                    DeepStatusRow("All-files access",
                        when {
                            state.allFilesPermission && state.allFilesUsable -> "Working observation"
                            state.allFilesPermission -> "Permission granted"
                            else -> "Not granted"
                        }, "Android permission and local provider usability are separate checks")
                    DeepStatusRow("Shizuku",
                        when {
                            !state.shizukuInstalled -> "Not installed"
                            !state.shizukuRunning -> "Not running"
                            state.shizukuPermission -> "Permission granted"
                            else -> "Not authorized"
                        }, "No permission request or privileged service bind from this screen")
                    DeepStatusRow("Root", if (state.rootExplicitlyEnabled) "Explicitly enabled" else "Off",
                        "Never automatically requested or enabled")
                }
            }
        }
        Text(if (isQueue)
            "For a complete operation history and recovery journal indicators, open Operation center."
            else "Use Advanced settings to choose a directory or explicitly request permissions.",
            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
        if (isQueue) {
            Button(onClick = onOpenOperations, modifier = Modifier.fillMaxWidth()
                .testTag("cinderbox.deep.open-operations")) { Text("Open Operation center") }
        } else {
            Button(onClick = onOpenAdvancedSettings, modifier = Modifier.fillMaxWidth()
                .testTag("cinderbox.deep.open-settings")) { Text("Review access settings") }
            OutlinedButton(onClick = onOpenHealth, modifier = Modifier.fillMaxWidth()) {
                Text("Inspect installation health")
            }
        }
    }
}
