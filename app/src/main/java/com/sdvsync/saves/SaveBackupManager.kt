package com.sdvsync.saves

import android.content.Context
import com.sdvsync.logging.AppLogger
import java.io.File
import java.nio.file.Files
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class SaveBackupManager(private val context: Context) {

    companion object {
        private const val TAG = "BackupManager"
        const val DEFAULT_MAX_BACKUPS = 7
        const val MIN_MAX_BACKUPS = 1
        const val MAX_MAX_BACKUPS = 20
        private const val PREF_NAME = "backup_prefs"
        private const val KEY_MAX_BACKUPS = "max_backups"
        private val DATE_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm-ss-SSSSSSSSS")
    }

    var maxBackups: Int = DEFAULT_MAX_BACKUPS
        private set

    init {
        maxBackups = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getInt(KEY_MAX_BACKUPS, DEFAULT_MAX_BACKUPS)
    }

    private val backupRoot: File
        get() = File(context.filesDir, "backups").also { it.mkdirs() }

    private val restoreTransaction = SaveRestoreTransaction(context.filesDir)

    /** Block unrelated backup writes while an interrupted local restore needs review. */
    @Synchronized fun recoverInterruptedLocalRestore(): Boolean = restoreTransaction.recover()

    private fun safeName(name: String) {
        require(name.isNotBlank() && name != "." && name != ".." &&
            '/' !in name && '\\' !in name && '\u0000' !in name) { "Unsafe backup name" }
    }

    /**
     * Update the max backup count and immediately prune all save folders.
     */
    fun setMaxBackupsAndPrune(count: Int) {
        maxBackups = count.coerceIn(MIN_MAX_BACKUPS, MAX_MAX_BACKUPS)
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putInt(KEY_MAX_BACKUPS, maxBackups).apply()
        pruneAllSaves()
    }

    /**
     * Prune backups across all save folders to the current maxBackups limit.
     */
    fun pruneAllSaves() {
        backupRoot.listFiles()?.filter { it.isDirectory }?.forEach { saveDir ->
            pruneBackups(saveDir.name)
        }
    }

    /**
     * Create a backup of a local save folder.
     * Returns the backup directory path.
     */
    fun backupSave(saveDir: File): File? {
        check(recoverInterruptedLocalRestore()) { "Previous save restore needs review" }
        safeName(saveDir.name)
        var sourcePart: File? = saveDir.absoluteFile
        while (sourcePart != null) {
            require(!java.nio.file.Files.isSymbolicLink(sourcePart.toPath())) { "Save path contains a symlink" }
            sourcePart = sourcePart.parentFile
        }
        if (!saveDir.exists() || !saveDir.isDirectory) return null
        val sources = saveDir.listFiles() ?: error("Cannot read save folder")
        val bytesNeeded = sources.fold(0L) { total, file ->
            require(file.isFile && !java.nio.file.Files.isSymbolicLink(file.toPath())) {
                "Source save contains an unsafe file"
            }
            Math.addExact(total, file.length())
        }
        val space = com.sdvsync.local.StoragePlanner.plan(backupRoot, bytesNeeded)
        check(space.sufficient == true) { "Insufficient storage for backup: ${space.detail}" }

        AppLogger.d(TAG, "backupSave: starting backup of ${saveDir.name}")
        val backupDir = createBackupDirectory(saveDir.name)

        try {
            saveDir.listFiles()?.forEach { file ->
                if (file.isFile) {
                    file.copyTo(File(backupDir, file.name), overwrite = true)
                }
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "backupSave: failed for ${saveDir.name}", e)
            backupDir.deleteRecursively()
            throw e
        }

        pruneBackups(saveDir.name)
        AppLogger.d(TAG, "backupSave: completed at ${backupDir.absolutePath}")
        return backupDir
    }

    /**
     * Create a backup from in-memory save data.
     * Cleans up partial writes on failure.
     */
    fun backupSaveData(saveFolderName: String, files: Map<String, ByteArray>): File {
        check(recoverInterruptedLocalRestore()) { "Previous save restore needs review" }
        safeName(saveFolderName)
        files.keys.forEach(::safeName)
        val bytesNeeded = files.values.fold(0L) { total, data -> Math.addExact(total, data.size.toLong()) }
        val space = com.sdvsync.local.StoragePlanner.plan(backupRoot, bytesNeeded)
        check(space.sufficient == true) { "Insufficient storage for backup: ${space.detail}" }
        AppLogger.d(TAG, "backupSaveData: starting backup of $saveFolderName (${files.size} files)")
        require(files.isNotEmpty()) { "Cannot back up an empty save" }
        val backupDir = createBackupDirectory(saveFolderName)

        try {
            for ((filename, data) in files) {
                File(backupDir, filename).writeBytes(data)
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "backupSaveData: failed for $saveFolderName", e)
            backupDir.deleteRecursively()
            throw e
        }

        pruneBackups(saveFolderName)
        AppLogger.d(TAG, "backupSaveData: completed at ${backupDir.absolutePath}")
        return backupDir
    }

    private fun createBackupDirectory(saveFolderName: String): File {
        val directory = File(backupRoot, saveFolderName)
        Files.createDirectories(directory.toPath())
        val timestamp = LocalDateTime.now().format(DATE_FORMAT)
        return Files.createTempDirectory(directory.toPath(), "$timestamp-").toFile()
    }

    /**
     * List available backups for a save, newest first.
     */
    fun listBackups(saveFolderName: String): List<File> {
        safeName(saveFolderName)
        val saveBackupDir = File(backupRoot, saveFolderName)
        if (!saveBackupDir.exists()) return emptyList()

        return saveBackupDir.listFiles()
            ?.filter { it.isDirectory }
            ?.sortedByDescending { it.name }
            ?: emptyList()
    }

    /**
     * Restore a backup to a target directory.
     */
    @Synchronized fun restoreBackup(backupDir: File, targetDir: File): Boolean {
        check(recoverInterruptedLocalRestore()) { "Previous restore needs manual recovery" }
        if (!backupDir.exists()) return false
        val root = backupRoot.canonicalFile
        val source = backupDir.canonicalFile
        require(source.path.startsWith(root.path + File.separator)) { "Backup outside retained storage" }
        safeName(targetDir.name)
        for (folder in listOf(backupDir, targetDir)) {
            var part: File? = folder.absoluteFile
            while (part != null) {
                require(!java.nio.file.Files.isSymbolicLink(part.toPath())) {
                    "Restore path contains a symlink"
                }
                part = part.parentFile
            }
        }
        // Retain an additional pre-restore snapshot before direct filesystem replacement.
        if (targetDir.isDirectory && !targetDir.listFiles().isNullOrEmpty()) {
            // Keep the chosen old backup until it has been read, even if retention is full.
            // This explicit pre-restore snapshot is pruned *after* the repair succeeds.
            val snapshotDir = createBackupDirectory(targetDir.name)
            try {
                val originals = targetDir.listFiles() ?: error("Cannot list current save")
                val backupSize = originals.fold(0L) { total, file ->
                    require(file.isFile && !java.nio.file.Files.isSymbolicLink(file.toPath())) {
                        "Current save contains an unsafe entry"
                    }
                    Math.addExact(total, file.length())
                }
                val space = com.sdvsync.local.StoragePlanner.plan(backupRoot, backupSize)
                check(space.sufficient == true) { "Insufficient storage for pre-restore snapshot: ${space.detail}" }
                originals.forEach { file ->
                    file.copyTo(File(snapshotDir, file.name), overwrite = false)
                }
            } catch (e: Exception) {
                snapshotDir.deleteRecursively()
                throw e
            }
        }
        val restored = restoreTransaction.restore(source, targetDir)
        pruneBackups(targetDir.name)
        return restored
    }

    private fun pruneBackups(saveFolderName: String) {
        val backups = listBackups(saveFolderName)
        if (backups.size > maxBackups) {
            val toPrune = backups.drop(maxBackups)
            AppLogger.d(TAG, "pruneBackups($saveFolderName): removing ${toPrune.size} old backups")
            toPrune.forEach { dir -> dir.deleteRecursively() }
        }
    }
}
