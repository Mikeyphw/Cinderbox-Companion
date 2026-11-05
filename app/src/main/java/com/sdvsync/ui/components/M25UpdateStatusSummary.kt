package com.sdvsync.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.sdvsync.mods.ModUpdateInsight
import com.sdvsync.mods.ModUpdateObservation
import com.sdvsync.mods.UpdateAssessment
import com.sdvsync.mods.models.InstalledMod

/** Synthetic-testable read-only summary; no install/permission controls. */
@Composable
fun M25UpdateStatusSummary(
    installed: List<InstalledMod>,
    observations: Map<String, ModUpdateObservation>,
    checkedAtMs: Long,
    refreshFailed: Boolean,
    nowMs: Long = System.currentTimeMillis()
) {
    var expanded by remember { mutableStateOf(false) }
    val entries = installed.sortedBy { it.manifest.name.lowercase(java.util.Locale.ROOT) }
        .take(50).map { mod ->
            val status = ModUpdateInsight.observationFor(
                mod.manifest.uniqueID, mod.manifest.version, observations)?.status
                ?: UpdateAssessment.UNKNOWN
            mod.manifest.name to status
        }
    val counts = UpdateAssessment.entries.associateWith { status ->
        entries.count { it.second == status }
    }
    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text("Update intelligence", style = MaterialTheme.typography.titleSmall)
        Text(ModUpdateInsight.freshness(checkedAtMs, nowMs),
            style = MaterialTheme.typography.bodySmall)
        if (refreshFailed) Text("Latest check failed — cached observations may be outdated",
            style = MaterialTheme.typography.bodySmall)
        Text("Newer: ${counts[UpdateAssessment.NEWER]} · Current: ${counts[UpdateAssessment.CURRENT]} " +
            "· Ahead: ${counts[UpdateAssessment.INSTALLED_AHEAD]}",
            style = MaterialTheme.typography.bodySmall)
        Text("Uncomparable: ${counts[UpdateAssessment.UNCOMPARABLE]} · " +
            "Unknown: ${counts[UpdateAssessment.UNKNOWN]}",
            style = MaterialTheme.typography.bodySmall)
        TextButton(onClick = { expanded = !expanded }) {
            Text(if (expanded) "Hide mod statuses" else "View mod statuses")
        }
        if (expanded) {
            entries.forEach { (name, status) ->
                Text("$name — ${ModUpdateInsight.label(status)}",
                    style = MaterialTheme.typography.bodySmall)
            }
            if (installed.size > entries.size) {
                Text("Showing first ${entries.size} mods", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
