package com.sdvsync.mods

import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModDependency
import com.sdvsync.mods.models.RemoteMod
import java.util.Locale

/** A passed manifest dependency check is not evidence of Android runtime compatibility. */
enum class RequirementVerdict { CHECKED, BLOCKED, REVIEW, UNKNOWN }

data class RequirementFinding(
    val title: String,
    val expected: String,
    val observed: String,
    val source: String,
    val verdict: RequirementVerdict,
    val explanation: String
)

data class ModRequirementsReport(
    val overall: RequirementVerdict,
    val installedSourceMatched: Boolean,
    val findings: List<RequirementFinding>
)

/** Pure, local-only evidence assessment. Never authorizes a mod operation. */
object ModRequirementsAssessor {
    private fun norm(text: String) = text.trim().lowercase(Locale.ROOT)

    fun assess(remote: RemoteMod, inventory: List<InstalledMod>?): ModRequirementsReport {
        val findings = mutableListOf<RequirementFinding>()
        val source = norm(remote.sourceId + ":" + remote.modId)
        val matches = inventory?.filter { norm(it.installedFrom.orEmpty()) == source }.orEmpty()
        val matched = inventory != null && matches.size == 1
        when {
            inventory == null -> findings += RequirementFinding(
                "Installed inventory", "Readable local inventory", "Unavailable", "Local storage",
                RequirementVerdict.UNKNOWN, "Local mod inventory could not be inspected.")
            matches.size > 1 -> findings += RequirementFinding(
                "Source association", "Unique source binding", "Multiple matches", "Stored source metadata",
                RequirementVerdict.BLOCKED, "Duplicate source bindings must be resolved.")
            matches.isEmpty() -> findings += RequirementFinding(
                "Installed manifest", "SMAPI manifest bound to provider listing", "Not matched",
                "Stored installed-from metadata", RequirementVerdict.UNKNOWN,
                "A Nexus listing is not proof of a validated installed manifest.")
            else -> {
                val mod = matches.single()
                findings += RequirementFinding("Local manifest", "Source-bound manifest",
                    mod.manifest.name + " v" + mod.manifest.version, "Installed SMAPI manifest",
                    RequirementVerdict.CHECKED, "Identity checked against stored source binding only.")
                val byId = inventory.orEmpty().groupBy { norm(it.manifest.uniqueID) }
                val requirements = mod.manifest.dependencies.map { it to "Dependency" } +
                    listOfNotNull(mod.manifest.contentPackFor?.let {
                        ModDependency(it.uniqueID, it.minimumVersion, true) to "Content-pack provider"
                    })
                for ((dep, role) in requirements) {
                    val providers = byId[norm(dep.uniqueID)].orEmpty()
                    val found = providers.singleOrNull()
                    val mandatory = dep.isRequired
                    val (verdict, observed, detail) = when {
                        providers.size > 1 -> Triple(
                            if (mandatory) RequirementVerdict.BLOCKED else RequirementVerdict.REVIEW,
                            "Duplicate providers", "Duplicate unique IDs make the provider ambiguous.")
                        found == null -> Triple(
                            if (mandatory) RequirementVerdict.BLOCKED else RequirementVerdict.REVIEW,
                            "Missing", "No matching installed provider found.")
                        !found.enabled -> Triple(
                            if (mandatory) RequirementVerdict.BLOCKED else RequirementVerdict.REVIEW,
                            found.manifest.version + " (disabled)", "Provider is disabled.")
                        dep.minimumVersion != null -> {
                            val compared = ModCompatibility.atLeast(found.manifest.version, dep.minimumVersion)
                            Triple(when (compared) {
                                true -> RequirementVerdict.CHECKED
                                false -> if (mandatory) RequirementVerdict.BLOCKED else RequirementVerdict.REVIEW
                                null -> RequirementVerdict.REVIEW
                            }, found.manifest.version, when (compared) {
                                true -> "Installed version satisfies the declared minimum."
                                false -> "Installed version is below the declared minimum."
                                null -> "Version comparison is ambiguous; manual review required."
                            })
                        }
                        else -> Triple(RequirementVerdict.CHECKED, found.manifest.version,
                            "Provider is present and enabled; no minimum version was declared.")
                    }
                    findings += RequirementFinding(role + ": " + dep.uniqueID,
                        (if (mandatory) "Required" else "Optional") +
                            (dep.minimumVersion?.let { " · ≥" + it } ?: ""),
                        observed, "Installed SMAPI manifests", verdict, detail)
                }
                mod.manifest.minimumApiVersion?.let {
                    findings += RequirementFinding("Minimum SMAPI", "At least " + it,
                        "Loader version not validated", "Installed mod manifest", RequirementVerdict.UNKNOWN,
                        "Loader version must be obtained from a trusted independent source.")
                }
                if (requirements.isEmpty()) findings += RequirementFinding(
                    "Declared dependencies", "None declared", "None", "Installed SMAPI manifest",
                    RequirementVerdict.CHECKED, "No declared dependency is not proof of runtime compatibility.")
            }
        }
        findings += RequirementFinding("Game version", "Compatible game build", "Not verified",
            "Local installation discovery", RequirementVerdict.UNKNOWN,
            "Detected game files do not establish the actual game version.")
        findings += RequirementFinding("SMAPI runtime", "Compatible loader build", "Not verified",
            "Local loader discovery", RequirementVerdict.UNKNOWN,
            "The installed loader version has not been validated.")
        findings += RequirementFinding("Android compatibility", "Verified Android execution", "Not qualified",
            "Hosted synthetic tests", RequirementVerdict.UNKNOWN,
            "Remote metadata and manifest dependencies cannot establish Android runtime support.")
        val outcome = when {
            findings.any { it.verdict == RequirementVerdict.BLOCKED } -> RequirementVerdict.BLOCKED
            findings.any { it.verdict == RequirementVerdict.REVIEW } -> RequirementVerdict.REVIEW
            else -> RequirementVerdict.UNKNOWN
        }
        return ModRequirementsReport(outcome, matched, findings)
    }
}
