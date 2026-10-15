package com.sdvsync.diagnostics

import android.content.Context
import java.io.File
import java.nio.file.Files
import java.nio.file.LinkOption

/** Checks only fixed app-private markers. Never reads journal contents or external paths. */
data class OperationCenterEvidence(val journals: Set<String>, val pendingModReview: Boolean)

object OperationCenterEvidenceReader {
    private val journals = mapOf(
        "m6-game-download.properties" to "download",
        "mod-operation.properties" to "mod_install",
        "m8-profile-transaction.properties" to "mod_profile",
        "m9-mod-batch.properties" to "mod_batch",
        "m10-game-repair.properties" to "game_repair",
        "m11-save-restore.properties" to "save_restore"
    )
    fun read(context: Context): OperationCenterEvidence {
        val root = context.filesDir
        fun present(name: String): Boolean = runCatching {
            Files.exists(File(root, name).toPath(), LinkOption.NOFOLLOW_LINKS)
        }.getOrDefault(false)
        return OperationCenterEvidence(
            journals.filterKeys(::present).values.toSet(),
            present("mod-review-pending.zip") || present("mod-review-pending.properties")
        )
    }
}
