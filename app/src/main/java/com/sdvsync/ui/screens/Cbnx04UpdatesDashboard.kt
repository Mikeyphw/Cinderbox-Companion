package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.sdvsync.mods.ModUpdatesDashboardPolicy
import com.sdvsync.mods.ModUpdateInsight
import com.sdvsync.ui.viewmodels.ModManagerState

/** Native Updates view; uses the app's existing VM and cache, never a new HTTP client. */
@Composable
internal fun Cbnx04UpdatesDashboard(
    state: ModManagerState,
    onCheckNow: () -> Unit,
    onIgnoreVersion: (String) -> Unit,
    onRestoreVersion: (String) -> Unit,
    onOpenNexusMod: (String) -> Unit
) {
    val dashboard = ModUpdatesDashboardPolicy.evaluate(
        state.installedMods, state.updateObservations, state.ignoredUpdates,
        state.lastUpdateCheckMs, System.currentTimeMillis())
    Column(Modifier.fillMaxWidth().testTag("cbnx04d.updates.dashboard"),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Mod updates", style = MaterialTheme.typography.titleLarge)
        Text("SMAPI checks mod versions, not exact Nexus file installations."
            , style = MaterialTheme.typography.bodySmall)
        Text(ModUpdateInsight.freshness(dashboard.checkTimeMs, System.currentTimeMillis()),
            style = MaterialTheme.typography.bodySmall,
            color = if (dashboard.freshness == "SMAPI_CACHE_FRESH")
                MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.error)
        Text("${dashboard.availableCount} available · ${dashboard.ignoredCount} ignored · " +
            "${dashboard.unknownCount} uncertain", style = MaterialTheme.typography.bodyMedium)
        Button(onClick = onCheckNow, enabled = !state.isLoading && !state.isCheckingUpdates &&
            state.installedMods.any { it.enabled },
            modifier = Modifier.fillMaxWidth().testTag("cbnx04d.updates.check-now")) {
            Text(if (state.isCheckingUpdates) "Checking updates…" else "Check for updates now")
        }
        if (state.isCheckingUpdates) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }
        state.updateError?.let { error ->
            Text(error.take(180), color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall)
        }
        when {
            state.isLoading -> Text("Loading installed mods…")
            dashboard.installedCount == 0 -> Text("No installed mods to check.")
            else -> {
                for (entry in dashboard.entries) {
                    Surface(shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                        modifier = Modifier.fillMaxWidth().testTag("cbnx04d.updates.item")) {
                        Column(Modifier.padding(12.dp),
                            verticalArrangement = Arrangement.spacedBy(5.dp)) {
                            Text(entry.title, style = MaterialTheme.typography.titleSmall)
                            Text("Installed mod version: ${entry.installedVersion}",
                                style = MaterialTheme.typography.bodySmall)
                            val label = when {
                                entry.ignored -> "Update ignored for this version"
                                entry.status == "NEWER" -> "Mod update available"
                                entry.status == "CURRENT" -> "Current at last check"
                                entry.status == "INSTALLED_AHEAD" -> "Installed version ahead"
                                entry.status == "DISABLED" -> "Disabled — not checked"
                                entry.status == "AMBIGUOUS" -> "Conflicting installed mod IDs"
                                entry.status == "UNCOMPARABLE" -> "Versions cannot be compared"
                                else -> "Update status unknown"
                            }
                            Text(label, style = MaterialTheme.typography.bodySmall)
                            if (entry.status == "NEWER" && entry.candidateVersion != null) {
                                Text("SMAPI candidate: ${entry.candidateVersion}",
                                    style = MaterialTheme.typography.bodySmall)
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    if (entry.ignored) {
                                        TextButton(onClick = { onRestoreVersion(entry.uniqueID) }) {
                                            Text("Restore update")
                                        }
                                    } else {
                                        TextButton(onClick = { onIgnoreVersion(entry.uniqueID) }) {
                                            Text("Ignore this version")
                                        }
                                    }
                                }
                            }
                            if (entry.nexusModId != null) {
                                OutlinedButton(onClick = { onOpenNexusMod(entry.nexusModId) }) {
                                    Text("View Nexus mod")
                                }
                            }
                        }
                    }
                }
                if (dashboard.additionalCount > 0) {
                    Text("${dashboard.additionalCount} more mods not shown here.",
                        style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Text("Viewing update statuses does not download or install mods. " +
            "Check now uses the existing SMAPI checker; automatic checks follow app settings.",
            style = MaterialTheme.typography.bodySmall)
    }
}
