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

/** One visible active transfer; durable records and service's FIFO hold additional jobs. */
class ModDownloadManager(private val context: Context) {
    companion object { internal val _progress = MutableStateFlow(ModDownloadProgress()) }
    val progress: StateFlow<ModDownloadProgress> = _progress.asStateFlow()

    @Synchronized
    fun startDownload(url: String, modName: String, modId: String, source: String,
                      fileId: String = "") {
        val journal = ModDownloadJournal(context)
        // Different file IDs queue normally; duplicate active requests are ignored.
        if (fileId.isNotBlank() && journal.list().any {
            it.source == source && it.modId == modId && it.fileId == fileId &&
                it.status in setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING")
        }) return
        val jobId = journal.create(modName, source, modId, fileId)
        try {
            // M4: check writable target and cache before scheduling work.
            // The service rechecks when the queued job actually executes.
            StoragePreflight.requireWritable(File(CinderboxPaths.MODS_DIR))
            StoragePreflight.requireWritable(context.cacheDir)
            ModDownloadService.start(context, url, modName, modId, source, fileId, jobId)
        } catch (_: Exception) {
            journal.update(jobId, "FAILED", detail = "Storage unavailable or Android could not start the download service")
            _progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                modName = modName, errorMessage = "Cannot start download; check storage access")
        }
    }

    fun cancelDownload() { ModDownloadService.stop(context) }
    fun resetProgress() { _progress.value = ModDownloadProgress() }
}
