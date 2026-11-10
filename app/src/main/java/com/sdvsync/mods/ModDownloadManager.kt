package com.sdvsync.mods

import android.content.Context
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.local.StoragePreflight
import java.io.File
import com.sdvsync.mods.models.ModDownloadProgress
import com.sdvsync.mods.models.ModDownloadState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Admission is journal-atomic; @Synchronized on this manager is NOT the concurrency boundary. */
class ModDownloadManager(private val context: Context) {
    companion object { internal val _progress = MutableStateFlow(ModDownloadProgress()) }
    val progress: StateFlow<ModDownloadProgress> = _progress.asStateFlow()

    fun startDownload(url: String, modName: String, modId: String, source: String,
                      fileId: String = ""): ModDownloadAdmission {
        // Storage preflight precedes journal allocation. A failed preflight leaves no ghost QUEUED row.
        val storageReady = runCatching {
            StoragePreflight.requireWritable(File(CinderboxPaths.MODS_DIR))
            StoragePreflight.requireWritable(context.cacheDir)
        }.isSuccess
        if (!storageReady) return refused("STORAGE_UNAVAILABLE", modName)
        if (source == "nexus" && !url.startsWith("https://", ignoreCase = true)) {
            return refused("INVALID_IDENTITY", modName)
        }
        val journal = ModDownloadJournal(context)
        val admission = try { journal.admit(modName, source, modId, fileId) }
                        catch (_: Exception) { ModDownloadAdmission(reason = "JOURNAL_UNAVAILABLE") }
        if (!admission.accepted) return refused(admission.reason, modName)
        val id = admission.jobId ?: return refused("JOURNAL_UNAVAILABLE", modName)
        return try {
            ModDownloadService.start(context, url, modName, modId, source, fileId, id)
            admission
        } catch (_: Exception) {
            // Do not report success if Android refused to start; this failed attempt stays auditable.
            journal.update(id, "FAILED", detail = "Android could not start download service")
            refused("START_FAILED", modName)
        }
    }

    private fun refused(reason: String, modName: String): ModDownloadAdmission {
        val outcome = ModDownloadAdmission(reason = reason)
        // Never change the progress of an unrelated transfer merely because admission was refused.
        if (reason == "STORAGE_UNAVAILABLE" || reason == "START_FAILED") {
            _progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                modName = modName, errorMessage = outcome.userMessage)
        }
        return outcome
    }

    fun pause(id: String) { ModDownloadService.pause(context, id) }
    fun resume(id: String) { ModDownloadService.resume(context, id) }
    fun cancelOne(id: String) { ModDownloadService.cancelOne(context, id) }
    fun move(id: String, delta: Int) {
        require(delta == -1 || delta == 1)
        ModDownloadService.move(context, id, delta)
    }
    fun cancelDownload() { ModDownloadService.stop(context) }
    fun resetProgress() { _progress.value = ModDownloadProgress() }
}
