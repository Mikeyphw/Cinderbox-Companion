package com.sdvsync.mods

import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModUpdateInfo
import java.util.Locale

/**
 * CB-NX04D: native, read-only presentation of the same app-owned SMAPI evidence
 * used by CB-NX04C. Never calls a provider, opens a file, or claims exact-file
 * installation. Status and candidate are UNKNOWN unless the observation is fresh,
 * identity-matched and version-consistent.
 */
object ModUpdatesDashboardPolicy {
    private const val MAX_MODS = 512
    private const val MAX_VISIBLE = 96
    private val nexusKey = Regex("(?i)^Nexus:([1-9][0-9]{0,11})$")

    data class Entry(
        val uniqueID: String,
        val title: String,
        val installedVersion: String,
        val candidateVersion: String?,
        val status: String,
        val nexusModId: String?,
        val ignored: Boolean
    )
    data class Dashboard(
        val freshness: String,
        val checkTimeMs: Long,
        val installedCount: Int,
        val availableCount: Int,
        val ignoredCount: Int,
        val unknownCount: Int,
        val additionalCount: Int,
        val entries: List<Entry>
    )

    fun evaluate(installed: List<InstalledMod>,
                 observations: Map<String, ModUpdateObservation>,
                 ignoredUpdates: Map<String, ModUpdateInfo>,
                 checkedAtMs: Long, nowMs: Long): Dashboard {
        val snapshot = NexusUpdateEvidence.Snapshot(checkedAtMs, observations)
        val freshness = NexusUpdateEvidence.freshness(snapshot, nowMs)
        val candidates = installed.take(MAX_MODS)
        val canonical = candidates.map { runCatching {
            ModUpdatePolicy.normalizedId(it.manifest.uniqueID)
        }.getOrNull() }
        val counts = canonical.filterNotNull().groupingBy { it }.eachCount()
        val rows = candidates.mapIndexed { index, mod ->
            val id = canonical[index]
            val ambiguous = id == null || counts[id] != 1
            val decision = when {
                !mod.enabled -> NexusUpdateEvidence.Decision("DISABLED")
                ambiguous -> NexusUpdateEvidence.Decision("AMBIGUOUS")
                else -> NexusUpdateEvidence.classify(snapshot, id!!, mod.manifest.version, nowMs)
            }
            // A disabled mod, duplicate unique ID or stale source must never appear actionable.
            val status = decision.status
            val ignored = status == "NEWER" && ignoredUpdates.values.any { update ->
                runCatching { ModUpdatePolicy.normalizedId(update.uniqueID) }.getOrNull() == id &&
                    update.installedVersion == mod.manifest.version &&
                    update.latestVersion == decision.candidate
            }
            val modIds = mod.manifest.updateKeys.mapNotNull { key ->
                nexusKey.matchEntire(key.trim())?.groupValues?.get(1)
            }.distinct()
            Entry(
                uniqueID = mod.manifest.uniqueID.take(128),
                title = mod.manifest.name.take(100).ifBlank { "Unnamed mod" },
                installedVersion = mod.manifest.version.take(80),
                candidateVersion = decision.candidate?.take(80),
                status = status,
                nexusModId = modIds.singleOrNull(),
                ignored = ignored
            )
        }
        val ordered = rows.sortedWith(compareBy<Entry> {
            when {
                it.status == "NEWER" && !it.ignored -> 0
                it.ignored -> 1
                it.status == "UNKNOWN" || it.status == "AMBIGUOUS" -> 2
                it.status == "UNCOMPARABLE" -> 3
                it.status == "DISABLED" -> 4
                else -> 5
            }
        }.thenBy { it.title.lowercase(Locale.ROOT) })
        return Dashboard(
            freshness = freshness,
            checkTimeMs = checkedAtMs,
            installedCount = installed.size,
            availableCount = rows.count { it.status == "NEWER" && !it.ignored },
            ignoredCount = rows.count { it.ignored },
            unknownCount = rows.count { it.status in setOf("UNKNOWN", "AMBIGUOUS", "UNCOMPARABLE") },
            additionalCount = (installed.size - MAX_MODS).coerceAtLeast(0) +
                (ordered.size - MAX_VISIBLE).coerceAtLeast(0),
            entries = ordered.take(MAX_VISIBLE)
        )
    }
}
