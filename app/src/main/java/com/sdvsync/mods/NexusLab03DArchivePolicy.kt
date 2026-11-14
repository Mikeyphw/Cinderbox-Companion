package com.sdvsync.mods

/** LAB03D archive provenance is local synthetic evidence, not an authenticated Nexus download. */
internal object NexusLab03DArchivePolicy {
    const val SOURCE_SCHEMA = "cbnx06-lab03-synthetic-v1"
    const val STAGE_SCHEMA = "cbnx06-lab03d-staged-synthetic-v1"
    const val SCOPE = "LAB_SYNTHETIC_ONLY"
    const val PROVENANCE = "LOCAL_SYNTHETIC_GENERATOR_ONLY"
    const val ENTRY = "CBNX06_LAB03_ONLY/manifest.json"
    const val MIN_ARCHIVE_BYTES = 128L
    const val MAX_ARCHIVE_BYTES = 16_384L
    private val digestPattern = Regex("[0-9a-f]{64}")

    /** Reject optimistic provenance, hash confusion, missing source, or misleading install flags. */
    fun validLocalReceipt(
        schema: String, scope: String, sourceSha256: String, stagedSha256: String,
        sourceBytes: Long, stagedBytes: Long, provenance: String,
        nexusVerified: Boolean, installed: Boolean, productionFilesExamined: Boolean
    ): Boolean = schema == STAGE_SCHEMA && scope == SCOPE && provenance == PROVENANCE &&
        digestPattern.matches(sourceSha256) && sourceSha256 == stagedSha256 &&
        sourceBytes in MIN_ARCHIVE_BYTES..MAX_ARCHIVE_BYTES && sourceBytes == stagedBytes &&
        !nexusVerified && !installed && !productionFilesExamined
}
