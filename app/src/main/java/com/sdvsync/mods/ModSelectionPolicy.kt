package com.sdvsync.mods

import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModProfile
import java.util.Locale

/** M25-03 R1 groups and bounded read-only plans. This class has no file access. */
enum class ModGroupMode(val label: String) {
    ALL("All mods"), BY_AUTHOR("By author"), FRAMEWORK("SMAPI mods"),
    CONTENT_PACK("Content packs"), UPDATE_ATTENTION("Update attention"),
    COMPATIBILITY("Compatibility warnings")
}

data class ModBulkPreview(
    val inventoryFingerprint: String,
    val selectedIds: List<String>,
    val intendedEnable: Boolean,
    val steps: List<ModProfileStep>,
    val issues: List<ModCompatibilityIssue>
) {
    val blockers: List<ModCompatibilityIssue> get() = issues.filter { it.blocking }
}

/** Deliberately no apply() function: a fingerprint is NOT a filesystem/journal witness. */
object ModSelectionPolicy {
    const val MAX_SELECTION = 512
    fun normalized(id: String): String = id.lowercase(Locale.ROOT)

    fun matches(mod: InstalledMod, mode: ModGroupMode,
        updateIds: Set<String>, issueNames: Set<String>): Boolean = when (mode) {
        ModGroupMode.ALL, ModGroupMode.BY_AUTHOR -> true
        ModGroupMode.FRAMEWORK -> mod.manifest.contentPackFor == null
        ModGroupMode.CONTENT_PACK -> mod.manifest.contentPackFor != null
        ModGroupMode.UPDATE_ATTENTION -> normalized(mod.manifest.uniqueID) in updateIds
        ModGroupMode.COMPATIBILITY -> normalized(mod.manifest.name) in issueNames
    }

    fun section(mod: InstalledMod, mode: ModGroupMode): String = when (mode) {
        ModGroupMode.BY_AUTHOR -> mod.manifest.author.ifBlank { "Unknown author" }
        ModGroupMode.FRAMEWORK -> "SMAPI mods"
        ModGroupMode.CONTENT_PACK -> "Content packs"
        ModGroupMode.UPDATE_ATTENTION -> "Updates"
        ModGroupMode.COMPATIBILITY -> "Compatibility warnings"
        ModGroupMode.ALL -> "Installed mods"
    }

    private fun safeName(s: String): Boolean = s.isNotBlank() && s != "." && s != ".." &&
        '/' !in s && '\\' !in s && s.none { it.isISOControl() }

    /** Plan ONLY. Folder bytes, symlinks and journal state must be independently verified by R2. */
    fun preview(mods: List<InstalledMod>, requestedIds: Set<String>, enable: Boolean): ModBulkPreview {
        val fingerprint = ModCompatibility.fingerprint(mods)
        val selected = requestedIds.map(::normalized).sorted()
        val issues = mutableListOf<ModCompatibilityIssue>()
        if (requestedIds.isEmpty()) issues += ModCompatibilityIssue("Selection", "No mods selected", true)
        if (requestedIds.size > MAX_SELECTION || mods.size > MAX_SELECTION)
            issues += ModCompatibilityIssue("Selection", "Inventory or selection exceeds 512 mods", true)
        val byId = mods.groupBy { normalized(it.manifest.uniqueID) }
        for (id in selected) {
            if (byId[id]?.size != 1) issues += ModCompatibilityIssue(id,
                "Missing or duplicate selected mod: $id", true)
        }
        val target = mods.filter { it.enabled }.map { normalized(it.manifest.uniqueID) }.toMutableSet()
        for (id in selected) if (enable) target.add(id) else target.remove(id)
        // Existing profile preview already audits proposed dependencies, version bounds and duplicates.
        val proposal = ModCompatibility.preview(mods, ModProfile(
            name = "Bulk preview", enabledModIds = target, createdAt = 0L,
            id = "m25-03-bulk-preview", modifiedAt = 0L))
        issues += proposal.issues
        val occupied = mods.map { it.folderName }.toSet()
        val sources = proposal.steps.map { it.fromFolder }.toSet()
        val destinations = mutableSetOf<String>()
        for (step in proposal.steps) {
            if (!safeName(step.fromFolder) || !safeName(step.toFolder) ||
                step.fromFolder == step.toFolder)
                issues += ModCompatibilityIssue(step.name, "Unsafe folder rename", true)
            if (!destinations.add(step.toFolder) ||
                (step.toFolder in occupied && step.toFolder !in sources))
                issues += ModCompatibilityIssue(step.name, "Destination folder collision", true)
        }
        return ModBulkPreview(fingerprint, selected, enable, proposal.steps, issues.distinct())
    }

    fun stillMatches(review: ModBulkPreview, mods: List<InstalledMod>): Boolean =
        review.inventoryFingerprint == ModCompatibility.fingerprint(mods)
}
