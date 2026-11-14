package com.sdvsync.cinderbox

import android.content.Context
import com.sdvsync.BuildConfig
import java.io.File
import java.nio.file.Files
import java.nio.file.Path

/**
 * Process-local, fail-closed storage boundary for the *full* Cinderbox lab build.
 * Production remains unchanged; a lab app must never use production game roots.
 * This is defense in depth, NOT a sandbox against root access or malicious mounts.
 */
object CinderboxLabBoundary {
    private const val LAB_ID = "com.sdvsync.cbnx06lab"
    @Volatile private var privateHome: File? = null
    @Volatile private var labHome: File? = null

    @Synchronized fun initialize(context: Context) {
        if (!BuildConfig.CBNX_LAB) return
        require(context.packageName == LAB_ID && BuildConfig.APPLICATION_ID == LAB_ID) {
            "LAB_APPLICATION_ID_MISMATCH"
        }
        val data = context.dataDir.canonicalFile
        val files = context.filesDir.canonicalFile
        require(files.parentFile == data && files.isDirectory) { "LAB_FILES_NOT_PRIVATE" }
        privateHome = data
        val proposed = File(files, "CBNX06_GAME_LAB")
        requirePrivate(proposed)
        require(proposed.mkdirs() || proposed.isDirectory) { "LAB_ROOT_UNAVAILABLE" }
        labHome = proposed.canonicalFile
        for (name in listOf("desktop/Mods", "desktop/Saves", "desktop/GameFiles", "smapi-internal")) {
            val directory = File(proposed, name)
            requirePrivate(directory)
            require(directory.mkdirs() || directory.isDirectory) { "LAB_TREE_UNAVAILABLE" }
        }
    }

    fun root(): String = if (!BuildConfig.CBNX_LAB) {
        "/storage/emulated/0/StardewValley"
    } else {
        checkNotNull(labHome) { "LAB_ROOT_NOT_INITIALIZED" }.absolutePath
    }

    /** Reject traversal, symlinked in-app folders and *any* target outside this package. */
    fun requirePrivate(candidate: File) {
        if (!BuildConfig.CBNX_LAB) return
        val home = checkNotNull(privateHome) { "LAB_PRIVATE_ROOT_NOT_INITIALIZED" }.toPath()
        val raw = candidate.absoluteFile.toPath()
        require(raw.isAbsolute && raw.normalize() == raw) { "LAB_PATH_NOT_NORMALIZED" }
        require(raw.startsWith(home) && raw != home) { "LAB_PATH_ESCAPES_PRIVATE_DATA" }
        var piece: Path = home
        for (name in home.relativize(raw)) {
            piece = piece.resolve(name)
            require(!Files.isSymbolicLink(piece)) { "LAB_SYMLINK_REFUSED" }
        }
        val canonical = candidate.canonicalFile.toPath()
        require(canonical.startsWith(home) && canonical != home) { "LAB_CANONICAL_ESCAPE" }
    }

    fun isPrivate(candidate: File): Boolean = if (!BuildConfig.CBNX_LAB) true
        else runCatching { requirePrivate(candidate); true }.getOrDefault(false)

    fun requireModsRoot(candidate: File) {
        if (!BuildConfig.CBNX_LAB) return
        requirePrivate(candidate)
        val expected = File(root(), "desktop/Mods")
        require(candidate.canonicalFile == expected.canonicalFile) { "LAB_MODS_ROOT_MISMATCH" }
    }
}
