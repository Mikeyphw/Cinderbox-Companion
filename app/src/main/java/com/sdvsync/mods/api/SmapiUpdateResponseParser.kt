package com.sdvsync.mods.api

import com.sdvsync.mods.ModUpdateCheckResult
import com.sdvsync.mods.ModUpdateObservation
import com.sdvsync.mods.ModUpdatePolicy
import com.sdvsync.mods.UpdateAssessment
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModUpdateInfo
import org.json.JSONArray

/** Strictly matches remote IDs to the requested installed inventory. */
object SmapiUpdateResponseParser {
    fun parse(
        installed: List<InstalledMod>,
        remote: JSONArray,
        checkedAtMs: Long
    ): ModUpdateCheckResult {
        require(checkedAtMs > 0L && installed.size <= 512 && remote.length() <= 1024) {
            "SMAPI observation limit exceeded"
        }
        val known = installed.associateBy { ModUpdatePolicy.normalizedId(it.manifest.uniqueID) }
        require(known.size == installed.size) { "Duplicate installed mod identifier" }
        val observations = linkedMapOf<String, ModUpdateObservation>()
        val updates = linkedMapOf<String, ModUpdateInfo>()
        val seenRemote = mutableSetOf<String>()
        known.forEach { (id, mod) ->
            observations[id] = ModUpdateObservation(mod.manifest.uniqueID, mod.manifest.version,
                null, UpdateAssessment.UNKNOWN)
        }
        for (index in 0 until remote.length()) {
            val record = remote.optJSONObject(index) ?: continue
            val id = record.optString("id", "")
            val canonical = runCatching { ModUpdatePolicy.normalizedId(id) }.getOrNull() ?: continue
            val mod = known[canonical] ?: continue
            require(seenRemote.add(canonical)) { "Duplicate SMAPI observation" }
            val candidate = record.optJSONObject("suggestedUpdate")
            val version = candidate?.optString("version", "")?.takeIf { it.isNotBlank() && it.length <= 80 }
            val status = ModUpdatePolicy.assess(mod.manifest.version, version)
            observations[canonical] = ModUpdateObservation(mod.manifest.uniqueID,
                mod.manifest.version, version?.take(80), status)
            if (status == UpdateAssessment.NEWER && version != null && version.length <= 80) {
                val source = mod.manifest.updateKeys.firstOrNull {
                    it.startsWith("Nexus:", ignoreCase = true)
                } ?: mod.manifest.updateKeys.firstOrNull().orEmpty()
                updates[mod.manifest.uniqueID] = ModUpdateInfo(
                    uniqueID = mod.manifest.uniqueID,
                    installedVersion = mod.manifest.version,
                    latestVersion = version,
                    updateUrl = candidate?.optString("url", "")?.takeIf { it.isNotBlank() },
                    source = source
                )
            }
        }
        return ModUpdateCheckResult(updates, observations, checkedAtMs)
    }
}
