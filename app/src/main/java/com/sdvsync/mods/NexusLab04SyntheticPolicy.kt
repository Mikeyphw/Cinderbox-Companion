package com.sdvsync.mods

/** LAB04: finite one-shot state machine; never interpret a synthetic receipt as Nexus provenance. */
internal object NexusLab04SyntheticPolicy {
    const val SCHEMA = "cbnx06-lab04-synthetic-transaction-v1"
    const val SCOPE = "LAB_SYNTHETIC_ONLY"
    const val SOURCE = "LOCAL_SYNTHETIC_GENERATOR_ONLY"
    const val FOLDER = "CBNX06_LAB03_ONLY"
    const val UNIQUE_ID = "CBNX06.LAB03.Synthetic"
    const val ARCHIVE_NAME = "lab03-synthetic.zip"
    private val digest = Regex("[0-9a-f]{64}")
    private val states = setOf("INSTALLING", "INSTALLED", "ROLLING_BACK", "ROLLED_BACK")

    fun validReceipt(schema: String, scope: String, provenance: String, sha256: String,
                     targetFolder: String, state: String, nexusVerified: Boolean,
                     productionFilesExamined: Boolean): Boolean =
        schema == SCHEMA && scope == SCOPE && provenance == SOURCE && digest.matches(sha256) &&
            targetFolder == FOLDER && state in states && !nexusVerified && !productionFilesExamined

    fun mayInstall(existingState: String?, emptyModsRoot: Boolean): Boolean =
        existingState == null && emptyModsRoot

    fun mayRollback(existingState: String?, validInstalledBytes: Boolean): Boolean =
        existingState == "INSTALLED" && validInstalledBytes

    fun allowedTransition(before: String?, after: String): Boolean =
        (before == null && after == "INSTALLING") ||
            (before == "INSTALLING" && after == "INSTALLED") ||
            (before == "INSTALLED" && after == "ROLLING_BACK") ||
            (before == "ROLLING_BACK" && after == "ROLLED_BACK")
}
