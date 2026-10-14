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

    fun startDownload(url: String, modName: String, modId: String, source: String) {
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
        ModDownloadService.start(context, url, modName, modId, source)
    }

    fun cancelDownload() {
        ModDownloadService.stop(context)
    }

    fun resetProgress() {
        _progress.value = ModDownloadProgress()
    }
}
