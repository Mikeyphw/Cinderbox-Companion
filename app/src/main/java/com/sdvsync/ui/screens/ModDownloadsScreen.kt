package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sdvsync.mods.ModDownloadJournal
import com.sdvsync.mods.ModDownloadManager
import com.sdvsync.mods.ModDownloadPreferences
import com.sdvsync.mods.ModDownloadRecord
import com.sdvsync.mods.ModQueueControlPolicy
import com.sdvsync.mods.ModReviewQueue
import com.sdvsync.mods.api.NexusBrowserHandoff
import com.sdvsync.mods.api.NexusBrowserLauncher
import com.sdvsync.mods.models.ModDownloadState
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import org.koin.compose.koinInject
import org.koin.androidx.compose.koinViewModel
import com.sdvsync.ui.viewmodels.ModManagerViewModel

/** Native, actionable and restart-aware mod downloads. No guessed remote completion. */
@Composable
fun ModDownloadsScreen(
    onBack: () -> Unit,
    onReview: () -> Unit,
    onOpenMod: (String) -> Unit,
    onOpenOperations: () -> Unit,
    selectedJobId: String? = null
) {
    val context = LocalContext.current
    val journal = remember(context) { ModDownloadJournal(context) }
    val manager: ModDownloadManager = koinInject()
    val reviewModel: ModManagerViewModel = koinViewModel()
    val reviewState by reviewModel.state.collectAsState()
    val progress by manager.progress.collectAsState()
    val revision by ModDownloadJournal.revision.collectAsState()
    val records = remember(revision) { journal.list() }
    val reviewQueue = remember(context) { ModReviewQueue(context.filesDir) }
    val reviewCount = remember(revision) { reviewQueue.pendingCount() }
    val reviewHead = remember(revision) { reviewQueue.receipt() }
    val previewMatchesCurrentArchive = reviewState.pendingDigest == reviewHead.sha256 &&
        reviewState.pendingModId == reviewHead.modId &&
        reviewState.pendingFileId == reviewHead.fileId &&
        reviewState.pendingLabel == reviewHead.name
    var reviewOpen by remember { mutableStateOf(false) }
    // ZIP previews can be expensive. Do not re-preview on each persisted byte update.
    LaunchedEffect(reviewHead.jobId, reviewHead.sha256, reviewCount) {
        if (reviewCount > 0) reviewModel.refreshSafetyState()
    }
    val showReview = {
        reviewModel.refreshSafetyState()
        reviewOpen = true
    }
    var approvalRequired by remember(context) { mutableStateOf(ModDownloadPreferences.requiresApproval(context)) }
    val approvalRevision by ModDownloadPreferences.revision.collectAsState()
    LaunchedEffect(approvalRevision) {
        approvalRequired = ModDownloadPreferences.requiresApproval(context)
    }
    var filter by remember { mutableStateOf("All") }
    var preferenceError by remember { mutableStateOf(false) }

    val attention = records.count { it.status in setOf("REVIEW_REQUIRED", "BLOCKED", "FAILED", "INTERRUPTED", "VERIFY_REQUIRED") }
    val pausedCount = records.count { it.status == "PAUSED" }
    val current = records.count { it.status in setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING") }
    val visible = records.filter { record -> when (filter) {
        "Active" -> record.status in setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING", "PAUSED")
        "Attention" -> record.status in setOf("REVIEW_REQUIRED", "BLOCKED", "FAILED", "INTERRUPTED", "VERIFY_REQUIRED")
        "Finished" -> record.status in setOf("INSTALLED", "COMPLETED", "CANCELLED", "DISCARDED")
        else -> true
    } }

    if (reviewOpen) {
        AlertDialog(
            onDismissRequest = { if (!reviewState.isApplyingReview) reviewOpen = false },
            title = { Text("Review downloaded archive") },
            text = {
                Column(Modifier.heightIn(max = 300.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text(reviewState.pendingLabel.ifBlank { reviewHead.name })
                    if (reviewHead.modId.isNotBlank()) Text("Nexus mod: ${reviewHead.modId}")
                    if (reviewHead.fileId.isNotBlank()) Text("Exact file: ${reviewHead.fileId}")
                    if (reviewHead.sha256.isNotBlank()) Text("SHA-256: ${reviewHead.sha256}",
                        style = MaterialTheme.typography.bodySmall)
                    val preview = reviewState.pendingPreview.takeIf {
                        previewMatchesCurrentArchive && reviewCount > 0
                    }
                    if (preview == null) {
                        Text("This archive has no valid install preview. Installation is disabled; you may discard it.",
                            color = MaterialTheme.colorScheme.error)
                    } else {
                        Text("Changes to review before installation:")
                        preview.changes.take(15).forEach { c ->
                            Text("${c.action}: ${c.modName} → ${c.folder}",
                                style = MaterialTheme.typography.bodySmall)
                        }
                    }
                    reviewState.importMessage?.let { Text(it, color = Dark.Muted) }
                    TextButton(onClick = { reviewOpen = false; onReview() }) {
                        Text("Advanced local manager")
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { reviewModel.confirmPendingReview() },
                    enabled = reviewState.pendingPreview != null &&
                        previewMatchesCurrentArchive && reviewCount > 0 && !reviewState.isApplyingReview) {
                    Text("Install reviewed archive")
                }
            },
            dismissButton = {
                Row {
                    TextButton(onClick = { reviewModel.discardPendingReview() },
                        enabled = !reviewState.isApplyingReview) { Text("Discard") }
                    TextButton(onClick = { reviewOpen = false },
                        enabled = !reviewState.isApplyingReview) { Text("Close") }
                }
            }
        )
    }
    Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()
        .verticalScroll(rememberScrollState())
        .padding(horizontal = 18.dp, vertical = 12.dp)
        .testTag("cinderbox.screen.download-queue-v2"),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        TextButton(onClick = onBack) { Text("‹ Back") }
        Text("Downloads", style = MaterialTheme.typography.headlineMedium,
            color = Dark.Ink, fontWeight = FontWeight.Bold)
        Text("$current active · $pausedCount paused · $attention need attention · $reviewCount awaiting review",
            style = MaterialTheme.typography.bodyMedium, color = Dark.Muted)

        if (reviewCount > 0) {
            Surface(color = Dark.Paper, border = BorderStroke(1.dp, Dark.Line),
                shape = RoundedCornerShape(14.dp), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Mod archive needs attention", color = Dark.Ink,
                        style = MaterialTheme.typography.titleSmall)
                    Text("$reviewCount archive(s) are safely stored. Inspect and install or discard them.",
                        style = MaterialTheme.typography.bodySmall, color = Dark.Muted)
                    Button(onClick = showReview, modifier = Modifier.fillMaxWidth()
                        .testTag("cbnx02.downloads.review")) { Text("Review and install next archive") }
                }
            }
        }

        Surface(color = Dark.Paper, shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, Dark.Line)) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("Require approval before installing", color = Dark.Ink,
                            style = MaterialTheme.typography.bodyMedium)
                        Text("Off by default. Auto-install still validates the archive, checks destination changes, and retains rollback snapshots.",
                            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                    }
                    Switch(checked = approvalRequired, onCheckedChange = { checked ->
                        val result = runCatching { ModDownloadPreferences.setRequiresApproval(context, checked) }
                        if (result.isSuccess) { approvalRequired = checked; preferenceError = false }
                        else preferenceError = true
                    }, modifier = Modifier.testTag("cbnx02.downloads.approval-toggle"))
                }
                if (preferenceError) Text("Could not save this setting", color = MaterialTheme.colorScheme.error)
            }
        }

        Row(Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            for (option in listOf("All", "Active", "Attention", "Finished")) {
                FilterChip(selected = filter == option, onClick = { filter = option },
                    label = { Text(option, style = MaterialTheme.typography.labelSmall) })
            }
        }

        if (visible.isEmpty()) {
            Surface(color = Dark.Paper, shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
                Text("No downloads in this view. New Nexus downloads appear here automatically.",
                    color = Dark.Muted, modifier = Modifier.padding(16.dp))
            }
        }
        // Completion notifications prioritize the exact job, not an unrelated FIFO item.
        for (record in visible.sortedBy { if (it.id == selectedJobId) 0 else 1 }) {
            DownloadRecordCard(record, progress.state, showReview, onOpenMod,
                onCancel = { manager.cancelDownload() },
                isReviewHead = record.id == reviewHead.jobId,
                fromNotification = record.id == selectedJobId,
                onPause = { manager.pause(record.id) },
                onResume = { manager.resume(record.id) },
                onCancelOne = { manager.cancelOne(record.id) },
                onMoveUp = { manager.move(record.id, -1) },
                onMoveDown = { manager.move(record.id, 1) },
                onRetryExact = {
                    NexusBrowserHandoff.createUrl(record.modId, record.fileId)?.let { url ->
                        NexusBrowserLauncher.open(context, url)
                    }
                })
        }
        if (records.any { it.status in setOf("INSTALLED", "COMPLETED", "CANCELLED", "FAILED", "DISCARDED") }) {
            OutlinedButton(onClick = { journal.clearHistory() }, modifier = Modifier.fillMaxWidth()) {
                Text("Clear finished history")
            }
        }
        OutlinedButton(onClick = onOpenOperations, modifier = Modifier.fillMaxWidth()) {
            Text("Open operation center")
        }
    }
}

@Composable
internal fun DownloadRecordCard(record: ModDownloadRecord, current: ModDownloadState,
    onReview: () -> Unit, onOpenMod: (String) -> Unit, onCancel: () -> Unit,
    isReviewHead: Boolean = true, fromNotification: Boolean = false,
    onPause: () -> Unit = {}, onResume: () -> Unit = {},
    onCancelOne: () -> Unit = {}, onMoveUp: () -> Unit = {},
    onMoveDown: () -> Unit = {}, onRetryExact: () -> Unit = {}) {
    val active = record.status in setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING")
    val needsReview = record.status in setOf("REVIEW_REQUIRED", "BLOCKED")
    val fraction = if (record.total > 0) (record.received.toFloat() / record.total)
        .coerceIn(0f, 1f) else null
    Surface(color = Dark.Paper, shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()
            .testTag("cbnx02.downloads.job")) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            if (fromNotification) Text("Opened from notification", color = Dark.Forest,
                style = MaterialTheme.typography.labelSmall)
            Text(record.name, color = Dark.Ink, style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold)
            Text(buildString {
                append(record.source.ifBlank { "Mod" })
                if (record.modId.isNotBlank()) append(" · Mod ${record.modId}")
                if (record.fileId.isNotBlank()) append(" · File ${record.fileId}")
            }, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            Text(record.status.lowercase().replace('_', ' ').replaceFirstChar { it.uppercase() },
                color = Dark.Forest, style = MaterialTheme.typography.labelMedium)
            if (record.detail.isNotBlank()) Text(record.detail, color = Dark.Muted,
                style = MaterialTheme.typography.bodySmall)
            if (record.status == "PAUSED") {
                Text("Resume only works during this app session, restarts from zero, and may require fresh Nexus authorization.",
                    style = MaterialTheme.typography.bodySmall, color = Dark.Muted)
            }
            if (record.status == "INTERRUPTED") {
                Text("Authorization is not retained after a restart. Reopen the exact file in Firefox.",
                    style = MaterialTheme.typography.bodySmall, color = Dark.Muted)
            }
            if (record.status == "VERIFY_REQUIRED") {
                Text("Installation outcome needs inspection. Check installed Mods and the operation center before retrying.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            }
            if (active && record.status == "DOWNLOADING") {
                if (fraction != null) LinearProgressIndicator(progress = { fraction },
                    modifier = Modifier.fillMaxWidth())
                else LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                Text(if (record.total > 0) "${record.received / 1024} / ${record.total / 1024} KiB"
                    else "${record.received / 1024} KiB received",
                    color = Dark.Muted, style = MaterialTheme.typography.labelSmall)
            }
            Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically) {
                if (needsReview && isReviewHead) Button(onClick = onReview,
                    modifier = Modifier.testTag("cbnx02.downloads.review-item")) {
                    Text("Review and install")
                }
                if (needsReview && !isReviewHead) {
                    Text("Waiting for earlier reviews", color = Dark.Muted,
                        style = MaterialTheme.typography.labelSmall)
                }
                if (record.modId.isNotBlank()) {
                    OutlinedButton(onClick = { onOpenMod(record.modId) }) { Text("Mod details") }
                }
                if (record.status == "DOWNLOADING" && current == ModDownloadState.DOWNLOADING) {
                    TextButton(onClick = onCancel) { Text("Cancel all transfers") }
                }
                if (record.status == "QUEUED") {
                    TextButton(onClick = onMoveUp, modifier = Modifier.testTag("cbnx02b.queue.up")) {
                        Text("Move up")
                    }
                    TextButton(onClick = onMoveDown, modifier = Modifier.testTag("cbnx02b.queue.down")) {
                        Text("Move down")
                    }
                }
                if (record.status in setOf("QUEUED", "DOWNLOADING")) {
                    TextButton(onClick = onPause, modifier = Modifier.testTag("cbnx02b.queue.pause")) {
                        Text("Pause")
                    }
                }
                if (record.status == "PAUSED") {
                    TextButton(onClick = onResume, modifier = Modifier.testTag("cbnx02b.queue.resume")) {
                        Text("Resume from start")
                    }
                }
                if (record.status in setOf("QUEUED", "DOWNLOADING", "PAUSED")) {
                    TextButton(onClick = onCancelOne, modifier = Modifier.testTag("cbnx02b.queue.cancel-one")) {
                        Text("Cancel this")
                    }
                }
                if (record.source == "nexus" &&
                    ModQueueControlPolicy.freshLinkAllowed(record.source, record.modId, record.fileId, record.status)) {
                    TextButton(onClick = onRetryExact, modifier = Modifier.testTag("cbnx02b.queue.retry-exact")) {
                        Text("Fresh link in Firefox")
                    }
                }
            }
        }
    }
}
