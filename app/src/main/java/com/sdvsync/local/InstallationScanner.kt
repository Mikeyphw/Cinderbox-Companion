package com.sdvsync.local

import com.sdvsync.cinderbox.CinderboxPaths
import java.io.File
import java.nio.file.Files

/** Detection is read-only; a directory's presence is never proof of file integrity. */
enum class InstallHealth { MISSING, INACCESSIBLE, INCOMPLETE, DETECTED, STRUCTURALLY_VALID }

data class InstallAssessment(val health: InstallHealth, val details: String, val location: String) {
    val usable: Boolean get() = health == InstallHealth.STRUCTURALLY_VALID
}

data class InstallationSnapshot(
    val selectedGame: InstallAssessment,
    val cinderboxGame: InstallAssessment,
    val smapi: InstallAssessment,
    val cinderboxApp: InstallAssessment,
    val storage: StorageCheck
)

/** Never follows a symlink in a directory being evaluated for direct modification. */
object InstallationScanner {
    private val gameDlls = listOf(
        "Stardew Valley.dll", "StardewValley.GameData.dll", "BmFont.dll",
        "xTile.dll", "Lidgren.Network.dll"
    )

    fun game(folder: File): InstallAssessment {
        val root = if (File(folder, "Stardew Valley").isDirectory &&
            !File(folder, "Stardew Valley.dll").exists()) File(folder, "Stardew Valley") else folder
        val location = root.absolutePath
        if (hasSymlinkComponent(root)) return InstallAssessment(InstallHealth.INACCESSIBLE, "Symbolic link; manual inspection required", location)
        if (!root.exists()) return InstallAssessment(InstallHealth.MISSING, "No game files found", location)
        if (!root.isDirectory || !root.canRead() || root.listFiles() == null)
            return InstallAssessment(InstallHealth.INACCESSIBLE, "Directory cannot be read", location)
        val children = root.listFiles() ?: return InstallAssessment(InstallHealth.INACCESSIBLE, "Directory cannot be listed", location)
        if (children.isEmpty()) return InstallAssessment(InstallHealth.MISSING, "Empty directory", location)
        val content = File(root, "Content")
        if (gameDlls.any { name ->
                val dll = File(root, name)
                hasSymlinkComponent(dll) || !dll.isFile || !dll.canRead() || dll.length() <= 0L
            } || !content.isDirectory || hasSymlinkComponent(content) ||
            content.listFiles().isNullOrEmpty()) {
            return InstallAssessment(InstallHealth.INCOMPLETE, "Some required DLLs or Content assets are missing; existing files will not be overwritten", location)
        }
        return InstallAssessment(InstallHealth.STRUCTURALLY_VALID,
            "Core DLLs and Content present; Steam manifest hash verification not performed", location)
    }

    fun smapi(folder: File = File(CinderboxPaths.SMAPI_DIR)): InstallAssessment {
        val location = folder.absolutePath
        if (hasSymlinkComponent(folder)) return InstallAssessment(InstallHealth.INACCESSIBLE, "Symbolic link; manual inspection required", location)
        if (!folder.exists()) return InstallAssessment(InstallHealth.MISSING, "SMAPI directory not found", location)
        if (!folder.isDirectory || !folder.canRead()) return InstallAssessment(InstallHealth.INACCESSIBLE, "SMAPI directory not accessible", location)
        val files = folder.listFiles() ?: return InstallAssessment(InstallHealth.INACCESSIBLE, "Cannot list SMAPI files", location)
        if (files.isEmpty()) return InstallAssessment(InstallHealth.INCOMPLETE, "SMAPI directory is empty", location)
        if (files.any { it.name.startsWith(".sdvsync-stage-") } ||
            File(folder.parentFile, ".${folder.name}.sdvsync-stage").exists() ||
            File(folder.parentFile, ".${folder.name}.sdvsync-backup").exists()) {
            return InstallAssessment(InstallHealth.INCOMPLETE, "Interrupted SMAPI transaction needs review", location)
        }
        val recognized = files.any { it.name.contains("smapi", ignoreCase = true) && it.isFile && it.length() > 0L }
        return if (recognized) InstallAssessment(InstallHealth.DETECTED,
            "SMAPI-like files detected; runtime/version compatibility not verified", location)
        else InstallAssessment(InstallHealth.INCOMPLETE, "No recognizable SMAPI binaries found", location)
    }

    fun scan(selectedGameDir: File, cinderboxInstalled: Boolean): InstallationSnapshot =
        InstallationSnapshot(
            selectedGame = game(selectedGameDir),
            cinderboxGame = game(File(CinderboxPaths.GAME_FILES_DIR)),
            smapi = smapi(),
            cinderboxApp = InstallAssessment(
                if (cinderboxInstalled) InstallHealth.DETECTED else InstallHealth.MISSING,
                if (cinderboxInstalled) "Cinderbox Android package detected; launch compatibility not verified"
                else "Cinderbox Android package not installed", "com.game.cinderbox"),
            storage = StoragePreflight.check(selectedGameDir)
        )

    private fun hasSymlinkComponent(file: File): Boolean {
        var current: File? = file.absoluteFile
        while (current != null) {
            if (Files.isSymbolicLink(current.toPath())) return true
            current = current.parentFile
        }
        return false
    }
}
