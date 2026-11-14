package com.sdvsync.mods

/** CB-NX05A. Interpretation only: verified private ZIP != Nexus signature != installation. */
internal object ModDownloadEvidencePolicy {
    data class Observation(
        val jobId: String,
        val modId: String,
        val fileId: String,
        val archiveState: String,
        val archiveQualified: Boolean,
        val archiveScope: String,
        val inventoryState: String,
        val modState: String,
        val exactFileInstalled: String
    )
    data class Details(val archive: String, val mod: String, val exactFile: String,
                       val journal: String, val verifiedAtScan: Boolean)
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    private val acceptedStates = setOf("QUEUED", "DOWNLOADING", "PAUSED", "INTERRUPTED",
        "VALIDATING", "REVIEW_REQUIRED", "BLOCKED", "INSTALLING", "INSTALLED",
        "COMPLETED", "FAILED", "CANCELLED", "DISCARDED", "VERIFY_REQUIRED")

    fun evaluate(jobId: String, source: String, modId: String, fileId: String, journalStatus: String,
                 observation: Observation?): Details {
        val unknown = Details("Archive proof unavailable", "SMAPI mod presence unknown",
            "Exact Nexus file installation not verified", "Journal status uncertain", false)
        if (source != "nexus" || !positiveId.matches(modId) || !positiveId.matches(fileId) ||
            journalStatus !in acceptedStates) return unknown
        val base = unknown.copy(journal = "Journal: " + journalStatus.replace('_', ' '))
        if (observation == null || observation.jobId != jobId ||
            observation.modId != modId || observation.fileId != fileId ||
            observation.exactFileInstalled != "UNKNOWN") return base
        val verified = observation.archiveState == "VERIFIED_AT_SCAN" && observation.archiveQualified &&
            observation.archiveScope == "LOCAL_ZIP_VS_APP_RECEIPT"
        val proof = when {
            verified ->
                    "Retained ZIP matched its app-owned receipt at scan time"
            observation.archiveState == "NO_RETAINED_ARCHIVE" && !observation.archiveQualified &&
                observation.archiveScope == "LOCAL_ZIP_VS_APP_RECEIPT" ->
                    "No retained ZIP proof for this job; download history is separate"
            else -> "Archive proof unavailable"
        }
        val manifest = if (observation.inventoryState == "QUALIFIED") {
            when (observation.modState) {
                "PRESENT" -> "SMAPI mod manifest linked and enabled (mod-level only)"
                "DISABLED_PRESENT" -> "SMAPI mod manifest linked but disabled (mod-level only)"
                "NOT_LINKED" -> "No linked SMAPI manifest observed; not proof of absence"
                "AMBIGUOUS" -> "Conflicting SMAPI mod links; presence not verified"
                else -> "SMAPI mod presence unknown"
            }
        } else "SMAPI mod presence unknown"
        return base.copy(archive = proof, mod = manifest,
            verifiedAtScan = verified)
    }
}
