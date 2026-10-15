package com.sdvsync.mods

import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModProfile
import java.security.MessageDigest
import java.util.Locale

/** Offline SMAPI-manifest dependency audit. No network or mutation. */
data class ModCompatibilityIssue(val mod: String, val message: String, val blocking: Boolean)

data class ModProfileStep(val uniqueId: String, val name: String, val fromFolder: String,
                          val toFolder: String, val enable: Boolean)

data class ModProfilePreview(val fingerprint: String, val steps: List<ModProfileStep>,
                             val issues: List<ModCompatibilityIssue>) {
    val blockers: List<ModCompatibilityIssue> get() = issues.filter { it.blocking }
}

object ModCompatibility {
    private fun id(value: String) = value.lowercase(Locale.ROOT)
    private val versionPattern = Regex("^[0-9]+(\\.[0-9]+){0,3}([.-][a-zA-Z0-9.-]+)?$")

    /** Returns null for unparseable versions: never guess that a dependency is safe. */
    fun atLeast(current: String, minimum: String): Boolean? {
        if (!versionPattern.matches(current) || !versionPattern.matches(minimum)) return null
        fun parts(value: String): List<Int>? {
            val numeric = value.takeWhile { it.isDigit() || it == '.' }.split('.')
            return numeric.map { it.toIntOrNull() ?: return null }.let { it + List(4 - it.size) { 0 } }
        }
        val a = parts(current) ?: return null
        val b = parts(minimum) ?: return null
        for (i in 0..3) {
            if (a[i] != b[i]) return a[i] > b[i]
        }
        val currentSuffix = current.dropWhile { it.isDigit() || it == '.' }
        val minimumSuffix = minimum.dropWhile { it.isDigit() || it == '.' }
        // Matching numeric components but differing prerelease identifiers are ambiguous.
        if (currentSuffix.isNotEmpty() && minimumSuffix.isNotEmpty() &&
            currentSuffix != minimumSuffix) return null
        return minimumSuffix.isNotEmpty() || currentSuffix.isEmpty()
    }

    fun fingerprint(mods: List<InstalledMod>): String {
        val entries = mods.map { mod ->
            val manifest = mod.manifest
            val deps = manifest.dependencies.map {
                listOf(id(it.uniqueID), it.minimumVersion.orEmpty(), it.isRequired.toString())
                    .joinToString(":" )
            }.sorted().joinToString(";")
            listOf(id(manifest.uniqueID), mod.folderName, mod.enabled.toString(),
                   manifest.version, manifest.minimumApiVersion.orEmpty(),
                   manifest.contentPackFor?.uniqueID.orEmpty(),
                   manifest.contentPackFor?.minimumVersion.orEmpty(), deps)
                .joinToString("\\u0000")
        }.sorted().joinToString("\\u000a")
        val bytes = MessageDigest.getInstance("SHA-256").digest(entries.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }

    /** Evaluate the proposed enabled set, not merely currently enabled mods. */
    fun audit(mods: List<InstalledMod>, enabledIds: Set<String> =
        mods.filter { it.enabled }.map { id(it.manifest.uniqueID) }.toSet()): List<ModCompatibilityIssue> {
        val installed = mods.groupBy { id(it.manifest.uniqueID) }
        val enabled = enabledIds.map(::id).toSet()
        val issues = mutableListOf<ModCompatibilityIssue>()
        for ((key, copies) in installed) {
            if (copies.size > 1) issues += ModCompatibilityIssue(copies.first().manifest.name,
                "Duplicate SMAPI UniqueID: $key", true)
        }
        for (mod in mods) {
            val manifest = mod.manifest
            if (id(manifest.uniqueID) !in enabled) continue
            val required = manifest.dependencies.filter { it.isRequired }
                .map { Triple(it.uniqueID, it.minimumVersion, "dependency") } +
                listOfNotNull(manifest.contentPackFor?.let {
                    Triple(it.uniqueID, it.minimumVersion, "content-pack provider")
                })
            for ((requiredId, version, role) in required) {
                val provider = installed[id(requiredId)]?.singleOrNull()
                when {
                    provider == null -> issues += ModCompatibilityIssue(manifest.name,
                        "Missing or duplicate $role: $requiredId", true)
                    id(provider.manifest.uniqueID) !in enabled -> issues += ModCompatibilityIssue(manifest.name,
                        "Disabled $role: $requiredId", true)
                    version != null -> when (atLeast(provider.manifest.version, version)) {
                        false -> issues += ModCompatibilityIssue(manifest.name,
                            "$role $requiredId requires $version (installed ${provider.manifest.version})", true)
                        null -> issues += ModCompatibilityIssue(manifest.name,
                            "Cannot compare $role version: $requiredId (${provider.manifest.version} vs $version)", true)
                        true -> Unit
                    }
                }
            }
            if (manifest.minimumApiVersion != null) {
                issues += ModCompatibilityIssue(manifest.name,
                    "Requires SMAPI ${manifest.minimumApiVersion}; installed SMAPI version not validated", false)
            }
        }
        return issues.distinct()
    }

    fun preview(mods: List<InstalledMod>, profile: ModProfile): ModProfilePreview {
        val target = profile.enabledModIds.map(::id).toSet()
        val currentById = mods.groupBy { id(it.manifest.uniqueID) }
        val errors = (target - currentById.keys).sorted().map { missing ->
            ModCompatibilityIssue(profile.name, "Profile references missing mod: $missing", true)
        }
        val steps = mods.filter { it.enabled != (id(it.manifest.uniqueID) in target) }
            .map { mod ->
                val enable = id(mod.manifest.uniqueID) in target
                val name = mod.folderName
                ModProfileStep(mod.manifest.uniqueID, mod.manifest.name, name,
                    if (enable) name.removePrefix(".") else ".$name", enable)
            }.sortedWith(compareBy<ModProfileStep> { it.enable }.thenBy { it.uniqueId })
        val destinationNames = steps.map { it.toFolder }
        val nameIssues = if (destinationNames.size != destinationNames.toSet().size) {
            listOf(ModCompatibilityIssue(profile.name, "Conflicting profile destination folders", true))
        } else emptyList()
        return ModProfilePreview(fingerprint(mods), steps,
            (errors + nameIssues + audit(mods, target)).distinct())
    }
}
