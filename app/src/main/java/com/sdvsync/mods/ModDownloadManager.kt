package com.sdvsync.mods

import android.content.Context
import java.io.File
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.local.StoragePreflight
import com.sdvsync.mods.models.ModDownloadState
import com.sdvsync.mods.models.ModDownloadProgress
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Manages mod download progress state.
 * Acts as a shared state holder between the download service and UI.
 */
class ModDownloadManager(private val context: Context) {
    companion object {
        internal val _progress = MutableStateFlow(ModDownloadProgress())
    }

    val progress: StateFlow<ModDownloadProgress> = _progress.asStateFlow()

    @Synchronized
    fun startDownload(url: String, modName: String, modId: String, source: String) {
        // Block a second intent before the foreground service is scheduled.
        if (_progress.value.state == ModDownloadState.DOWNLOADING ||
            _progress.value.state == ModDownloadState.EXTRACTING ||
            _progress.value.state == ModDownloadState.INSTALLING) return
        if (ModReviewQueue(context.filesDir).hasPending()) {
            _progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                errorMessage = "Review or discard the previous mod archive in Mods first")
            return
        }
        try {
            StoragePreflight.requireWritable(File(CinderboxPaths.MODS_DIR))
            StoragePreflight.requireWritable(context.cacheDir)
        } catch (e: IllegalStateException) {
            _progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                errorMessage = e.message ?: "Storage unavailable")
            return
        }
        _progress.value = ModDownloadProgress(state = ModDownloadState.DOWNLOADING, modName = modName)
        try {
            ModDownloadService.start(context, url, modName, modId, source)
        } catch (e: Exception) {
            _progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                modName = modName, errorMessage = "Could not start the download service")
        }
    }

    fun cancelDownload() {
        ModDownloadService.stop(context)
    }

    fun resetProgress() {
        _progress.value = ModDownloadProgress()
    }
}
