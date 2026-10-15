package com.sdvsync.diagnostics

/** Stable, non-identifying categories. No user-controlled text reaches cards or exports. */
enum class CenterStatus { ACTIVE, ACTION_REQUIRED, COMPLETED, IDLE }
data class CenterItem(
    val id: String,
    val title: String,
    val status: CenterStatus,
    val detail: String,
    val action: String,
    val percent: Int? = null
)

/** Pure policy: present only explicit, allowlisted operation categories and guidance. */
object OperationCenterPolicy {
    private val journalTitles = mapOf(
        "download" to "Interrupted game download",
        "mod_install" to "Mod installation recovery",
        "mod_profile" to "Mod profile recovery",
        "mod_batch" to "Multi-mod recovery",
        "game_repair" to "Game repair recovery",
        "save_restore" to "Save restoration recovery"
    )
    fun percent(fraction: Float): Int? =
        if (!fraction.isFinite()) null else (fraction.coerceIn(0f, 1f) * 100f).toInt()

    fun build(
        gameState: String,
        modState: String,
        smapiActive: Boolean,
        smapiError: Boolean,
        appDownloadActive: Boolean,
        pendingReview: Boolean,
        journals: Set<String>,
        syncOutcomes: List<String>,
        gamePercent: Int? = null,
        modPercent: Int? = null
    ): List<CenterItem> {
        val items = mutableListOf<CenterItem>()
        val gs = when (gameState) {
            "PREPARING", "DOWNLOADING", "VERIFYING", "COPYING" -> CenterStatus.ACTIVE
            "ERROR", "CANCELLED" -> CenterStatus.ACTION_REQUIRED
            "COMPLETED" -> CenterStatus.COMPLETED
            else -> CenterStatus.IDLE
        }
        items += CenterItem("game_download", "Steam game files", gs,
            when (gs) {
                CenterStatus.ACTIVE -> "Download, verification, or copying in progress."
                CenterStatus.ACTION_REQUIRED -> "Review the download screen, storage access, and any matching resume checkpoint."
                CenterStatus.COMPLETED -> "Latest observed game download completed."
                CenterStatus.IDLE -> "No game download currently reported."
            }, "Open Downloads", if (gs == CenterStatus.ACTIVE) gamePercent?.coerceIn(0, 100) else null)
        val ms = when (modState) {
            "DOWNLOADING", "EXTRACTING", "INSTALLING" -> CenterStatus.ACTIVE
            "REVIEW_REQUIRED", "ERROR" -> CenterStatus.ACTION_REQUIRED
            "COMPLETED" -> CenterStatus.COMPLETED
            else -> CenterStatus.IDLE
        }
        items += CenterItem("mod_download", "Mod downloads", ms,
            when (modState) {
                "REVIEW_REQUIRED" -> "An archive needs explicit review in Mods before installation."
                "ERROR" -> "Check Mods for a pending review and inspect storage access."
                "DOWNLOADING", "EXTRACTING", "INSTALLING" -> "Mod download or extraction in progress."
                "COMPLETED" -> "Latest observed mod download completed."
                else -> "No active mod download reported."
            }, "Open Mods", if (ms == CenterStatus.ACTIVE) modPercent?.coerceIn(0, 100) else null)
        if (smapiActive || smapiError) items += CenterItem("smapi", "SMAPI setup",
            if (smapiError) CenterStatus.ACTION_REQUIRED else CenterStatus.ACTIVE,
            if (smapiError) "Inspect SMAPI setup; do not replace files until recovery is reviewed."
            else "SMAPI download or extraction in progress.", "Open Downloads")
        if (appDownloadActive) items += CenterItem("cinderbox_apk", "Cinderbox download",
            CenterStatus.ACTIVE, "Cinderbox APK download in progress.", "Open Downloads")
        if (pendingReview) items += CenterItem("mod_review", "Mod archive awaiting approval",
            CenterStatus.ACTION_REQUIRED, "Review the archive and proposed changes in Mods, or discard it.", "Open Mods")
        for (id in journalTitles.keys) {
            if (id !in journals) continue
            items += CenterItem(id, journalTitles.getValue(id), CenterStatus.ACTION_REQUIRED,
                when (id) {
                    "download" -> "Check the original destination and options before resuming. Do not delete existing files."
                    "save_restore" -> "Check Backups and verify saves before attempting another restore."
                    "game_repair" -> "Review installation health and any interrupted repair before retrying."
                    else -> "Open Mods and review recovery status. Unknown folder changes require manual inspection."
                }, when (id) {
                    "download" -> "Open Downloads"
                    "game_repair" -> "Open Installation Health"
                    "save_restore" -> "Open Saves"
                    else -> "Open Mods"
                })
        }
        val lastSync = syncOutcomes.lastOrNull { it in setOf("SUCCESS", "ERROR", "CONFLICT", "STALE_PREVIEW") }
        if (lastSync != null) items += CenterItem("sync", "Recent Steam Cloud sync",
            when (lastSync) {
                "SUCCESS" -> CenterStatus.COMPLETED
                else -> CenterStatus.ACTION_REQUIRED
            }, when (lastSync) {
                "SUCCESS" -> "The latest recorded sync completed."
                "CONFLICT" -> "Review both save versions and backup history before proceeding."
                "STALE_PREVIEW" -> "The files changed after preview. Review the sync again."
                else -> "Review the sync log, connection, and save backups."
            }, "Open Sync Log")
        return items
    }
}
