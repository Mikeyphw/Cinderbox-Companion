package com.sdvsync.ui.viewmodels

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sdvsync.logging.AppLogger
import com.sdvsync.saves.BackupInfo
import com.sdvsync.saves.SaveBackupManager
import com.sdvsync.saves.SaveFileManager
import com.sdvsync.saves.SaveMetadata
import com.sdvsync.saves.SaveMetadataParser
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class BackupListState(
    val saveFolderName: String = "",
    val backups: List<BackupInfo> = emptyList(),
    val currentMetadata: SaveMetadata? = null,
    val isLoading: Boolean = true,
    val isRestoring: Boolean = false,
    val restoreResult: String? = null,
    val error: String? = null
)

class BackupListViewModel(
    private val context: Context,
    private val backupManager: SaveBackupManager,
    private val saveFileManager: SaveFileManager,
    private val metadataParser: SaveMetadataParser
) : ViewModel() {

    companion object {
        private const val TAG = "BackupListVM"
        private val BACKUP_DATE_FORMAT = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.US)
        private val DISPLAY_DATE_FORMAT = SimpleDateFormat("MMM d, yyyy 'at' h:mm a", Locale.US)
    }

    private val _state = MutableStateFlow(BackupListState())
    val state: StateFlow<BackupListState> = _state.asStateFlow()

    fun loadBackups(saveFolderName: String) {
        _state.update { it.copy(saveFolderName = saveFolderName, isLoading = true, error = null) }

        viewModelScope.launch(Dispatchers.IO) {
            try {
                // Get current local metadata
                val localSaves = saveFileManager.listLocalSaves()
                val currentMeta = localSaves.find { it.folderName == saveFolderName }?.metadata

                // List and parse backup info
                val backupDirs = backupManager.listBackups(saveFolderName)
                val backups = backupDirs.map { dir -> parseBackupInfo(dir) }

                _state.update {
                    it.copy(
                        backups = backups,
                        currentMetadata = currentMeta,
                        isLoading = false
                    )
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to load backups", e)
                _state.update { it.copy(isLoading = false, error = e.message ?: "Failed to load backups") }
            }
        }
    }

    fun restoreBackup(backupDir: File) {
        val saveFolderName = _state.value.saveFolderName
        _state.update { it.copy(isRestoring = true, restoreResult = null) }

        viewModelScope.launch(Dispatchers.IO) {
            try {
                check(backupManager.recoverInterruptedLocalRestore()) {
                    "Unresolved local save restore requires manual inspection"
                }
                require(backupManager.listBackups(saveFolderName).any {
                    it.canonicalFile == backupDir.canonicalFile
                }) { "Backup is not in the retained snapshots for this save" }
                val backupFiles = mutableMapOf<String, ByteArray>()
                backupDir.listFiles()?.forEach { file ->
                    require(file.isFile && !java.nio.file.Files.isSymbolicLink(file.toPath())) {
                        "Backup contains unsafe files"
                    }
                    saveFileManager.requireSafeName(file.name)
                    backupFiles[file.name] = file.readBytes()
                }
                check(backupFiles.isNotEmpty()) { "Backup is empty" }

                val currentFiles = saveFileManager.readLocalSave(saveFolderName)
                check(currentFiles.isNotEmpty()) {
                    "Cannot safely restore to a missing or unreadable save; inspect it manually"
                }
                // SAF/root/Shizuku paths cannot use local rename transactions. Retain the
                // original data and attempt compensating restore on write or verify failure.
                backupManager.backupSaveData(saveFolderName, currentFiles)
                AppLogger.d(TAG, "Preserved current save before restore")
                val restored = runCatching {
                    check(saveFileManager.writeLocalSave(saveFolderName, backupFiles)) { "Save write failed" }
                    val readBack = saveFileManager.readLocalSave(saveFolderName)
                    check(backupFiles.all { (name, data) ->
                        readBack[name]?.contentEquals(data) == true
                    }) { "Restored save did not verify against backup" }
                }
                if (restored.isFailure) {
                    val rollback = runCatching {
                        check(saveFileManager.writeLocalSave(saveFolderName, currentFiles)) {
                            "Original save recovery write failed"
                        }
                        val recovered = saveFileManager.readLocalSave(saveFolderName)
                        check(currentFiles.all { (name, data) ->
                            recovered[name]?.contentEquals(data) == true
                        }) { "Original save recovery did not verify" }
                    }
                    _state.update { it.copy(isRestoring = false,
                        restoreResult = if (rollback.isSuccess) "Restore failed; original save restored and verified"
                        else "Restore failed; current-save snapshot retained. Manual recovery required") }
                    return@launch
                }
                _state.update { it.copy(isRestoring = false, restoreResult = "Restore complete and verified") }
                loadBackups(saveFolderName)
            } catch (e: Exception) {
                AppLogger.e(TAG, "Restore failed", e)
                _state.update {
                    it.copy(isRestoring = false, restoreResult = "Restore failed: ${e.message}")
                }
            }
        }
    }

    fun clearRestoreResult() {
        _state.update { it.copy(restoreResult = null) }
    }

    private fun parseBackupInfo(dir: File): BackupInfo {
        val metadata = try {
            val infoFile = File(dir, "SaveGameInfo")
            if (infoFile.exists()) metadataParser.parseFromFile(infoFile) else null
        } catch (e: Exception) {
            null
        }

        val files = dir.listFiles()?.filter { it.isFile } ?: emptyList()
        val totalSize = files.sumOf { it.length() }

        return BackupInfo(
            backupDir = dir,
            timestamp = formatTimestamp(dir.name),
            metadata = metadata,
            fileCount = files.size,
            totalSize = totalSize
        )
    }

    private fun formatTimestamp(dirName: String): String = try {
        val date = BACKUP_DATE_FORMAT.parse(dirName)
        if (date != null) DISPLAY_DATE_FORMAT.format(date) else dirName
    } catch (_: Exception) {
        dirName
    }
}
