package com.sdvsync.fileaccess

import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.saves.SaveFileManager
import java.io.File

/** Restrict privileged filesystem IPC/shell operations to known Stardew save trees. */
internal object PrivilegedSavePaths {
    private val saveRoots: List<File> = listOf(
        File(SaveFileManager.SDV_SAVE_PATH),
        File(CinderboxPaths.SAVES_DIR),
        File(CinderboxPaths.LEGACY_SAVES_DIR)
    )

    /** Canonical paths reject ../ segments and symlinks escaping the allowed tree. */
    internal fun isWithin(root: File, candidate: File): Boolean = try {
        val allowed = root.canonicalFile.toPath()
        val requested = candidate.canonicalFile.toPath()
        requested == allowed || requested.startsWith(allowed)
    } catch (_: Exception) {
        false
    }

    fun requireAllowed(candidate: File): File {
        require(saveRoots.any { isWithin(it, candidate) }) {
            "Privileged file operation outside Stardew save directories"
        }
        return candidate.canonicalFile
    }

    fun requireChild(candidate: File): File {
        requireAllowed(candidate)
        require(saveRoots.none { it.canonicalFile == candidate.canonicalFile }) {
            "Refusing to modify a save directory root"
        }
        return candidate.canonicalFile
    }
}
