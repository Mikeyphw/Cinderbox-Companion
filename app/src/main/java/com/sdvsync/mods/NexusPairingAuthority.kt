package com.sdvsync.mods

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.file.Files
import java.util.Locale

/**
 * CB-NX04A: independent, READ-ONLY observation of installed SMAPI manifests.
 * Avoid the legacy installed-mod listing, which may rename disabled folders.
 * This does not read Nexus cookies, call remote APIs, repair folders or install files.
 */
internal object NexusPairingAuthority {
    private const val MAX_FOLDERS = 256
    private const val MAX_MANIFEST_BYTES = 32768L
    private const val MAX_EXPORTED_ITEMS = 128
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    private val uniqueId = Regex("[A-Za-z0-9_.-]{1,128}")
    private val versionPattern = Regex("[A-Za-z0-9.+_-]{1,80}")
    private val nexusKey = Regex("(?i)^Nexus:([1-9][0-9]{0,11})$")

    private data class Installed(val uniqueId: String, val version: String, val enabled: Boolean)
    private data class Inventory(val qualified: Boolean, val linked: Map<String, List<Installed>>)

    private fun JSONObject.stringCI(name: String): String? {
        val key = keys().asSequence().firstOrNull { it.equals(name, ignoreCase = true) } ?: return null
        return optString(key).takeIf { it.isNotBlank() }
    }

    private fun JSONObject.arrayCI(name: String): JSONArray? {
        val key = keys().asSequence().firstOrNull { it.equals(name, ignoreCase = true) } ?: return null
        return optJSONArray(key)
    }

    private fun readInventory(modsDir: File): Inventory {
        // Missing, inaccessible, or partially unreadable Mods/ is UNKNOWN, never empty.
        if (Files.isSymbolicLink(modsDir.toPath()) || !modsDir.isDirectory || !modsDir.canRead()) {
            return Inventory(false, emptyMap())
        }
        val children = modsDir.listFiles() ?: return Inventory(false, emptyMap())
        if (children.size > MAX_FOLDERS) return Inventory(false, emptyMap())
        val found = linkedMapOf<String, MutableList<Installed>>()
        return try {
            for (folder in children.sortedBy { it.name.lowercase(Locale.ROOT) }) {
                if (Files.isSymbolicLink(folder.toPath())) return Inventory(false, emptyMap())
                if (!folder.isDirectory) continue
                val manifest = File(folder, "manifest.json")
                if (Files.isSymbolicLink(manifest.toPath())) return Inventory(false, emptyMap())
                if (!manifest.exists()) continue
                if (!manifest.isFile || !manifest.canRead() ||
                    manifest.length() !in 2L..MAX_MANIFEST_BYTES) return Inventory(false, emptyMap())
                val json = JSONObject(manifest.readText(Charsets.UTF_8))
                val id = json.stringCI("UniqueID") ?: return Inventory(false, emptyMap())
                val version = json.stringCI("Version") ?: return Inventory(false, emptyMap())
                if (!uniqueId.matches(id) || !versionPattern.matches(version)) {
                    return Inventory(false, emptyMap())
                }
                val rawKeys = json.arrayCI("UpdateKeys") ?: continue
                if (rawKeys.length() > 32) return Inventory(false, emptyMap())
                val seen = mutableSetOf<String>()
                for (index in 0 until rawKeys.length()) {
                    val raw = rawKeys.optString(index, "")
                    val match = nexusKey.matchEntire(raw.trim()) ?: continue
                    val nexusId = match.groupValues[1]
                    if (positiveId.matches(nexusId) && seen.add(nexusId)) {
                        found.getOrPut(nexusId) { mutableListOf() }.add(
                            Installed(id.lowercase(Locale.ROOT), version, !folder.name.startsWith(".")))
                    }
                }
            }
            Inventory(true, found)
        } catch (_: Exception) {
            // An inaccessible manifest must not masquerade as a clean inventory.
            Inventory(false, emptyMap())
        }
    }

    /** No paths, UniqueIDs, cookies, archive hashes, tokens or arbitrary provider text in HTTP. */
    fun snapshot(records: List<ModDownloadRecord>, modsDir: File, observedAtMs: Long,
                 privateReviewRoot: File? = null): JSONObject {
        val inventory = readInventory(modsDir)
        val archiveProof = NexusArchiveProvenance.inspect(records, privateReviewRoot)
        val output = JSONArray()
        val jobs = records.filter { it.source == "nexus" &&
            positiveId.matches(it.modId) && positiveId.matches(it.fileId) }
            .sortedWith(compareByDescending<ModDownloadRecord> { it.updatedAt }.thenBy { it.id })
        val used = mutableSetOf<String>()
        val reportableDownload = setOf("VALIDATING", "REVIEW_REQUIRED", "BLOCKED", "INSTALLING", "INSTALLED")
        val linked = if (inventory.qualified) inventory.linked else emptyMap()

        fun append(modId: String, fileId: String, status: String, journalDownloaded: Boolean, jobId: String?) {
            if (output.length() >= MAX_EXPORTED_ITEMS) return
            val key = "$modId/$fileId"
            if (!used.add(key)) return
            val entries = linked[modId].orEmpty()
            val distinct = entries.map { it.uniqueId }.distinct()
            val manifestState = when {
                !inventory.qualified -> "UNKNOWN"
                entries.isEmpty() -> "NOT_LINKED"
                entries.size != 1 || distinct.size != 1 -> "AMBIGUOUS"
                entries.single().enabled -> "PRESENT"
                else -> "DISABLED_PRESENT"
            }
            val verified = archiveProof.available && jobId != null &&
                archiveProof.confirmedJobIds.contains(jobId)
            val proofState = when {
                !archiveProof.available -> "UNAVAILABLE"
                verified -> "VERIFIED_AT_SCAN"
                else -> "NO_RETAINED_ARCHIVE"
            }
            val row = JSONObject()
                .put("mod_id", modId).put("file_id", fileId)
                .put("journal_state", status)
                .put("journal_transfer_reported", journalDownloaded)
                .put("archive_checksum_qualified", verified)
                .put("archive_proof_state", proofState)
                .put("archive_proof_scope", "LOCAL_ZIP_VS_APP_RECEIPT")
                .put("installed_mod_state", manifestState)
                .put("exact_file_installed", "UNKNOWN")
                // No comparable Nexus file-version observation is available here.
                .put("update_state", "UNKNOWN")
            if (manifestState in setOf("PRESENT", "DISABLED_PRESENT")) {
                row.put("installed_version", entries.single().version)
            }
            output.put(row)
        }
        for (job in jobs) {
            append(job.modId, job.fileId, job.status, job.status in reportableDownload, job.id)
        }
        for (id in linked.keys.sortedWith(compareBy<String> { it.length }.thenBy { it })) {
            if (positiveId.matches(id)) append(id, "", "NO_EXACT_FILE_RECEIPT", false, null)
        }
        return JSONObject()
            .put("schema", 1)
            .put("scope", "LOCAL_SMAPI_AND_JOURNAL")
            .put("observed_at_ms", observedAtMs.coerceAtLeast(0L))
            .put("inventory_state", if (inventory.qualified) "QUALIFIED" else "UNAVAILABLE")
            .put("remote_update_check", "NOT_PERFORMED")
            .put("items", output)
    }
}
