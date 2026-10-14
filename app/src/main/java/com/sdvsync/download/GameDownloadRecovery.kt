package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.Properties
import java.util.UUID

/**
 * Durable, app-private ownership record for an interrupted Steam download.
 * No Steam credentials or beta passwords are written to disk.
 * A checkpoint authorizes continuation only for the exact same destination,
 * Steam branch, OS, and verification choice. It never authorizes arbitrary files.
 */
data class GameDownloadCheckpoint(
    val directory: String,
    val branch: String,
    val os: String,
    val verify: Boolean,
    val token: String
) {
    fun matches(directory: File, branch: String, os: String, verify: Boolean): Boolean {
        val safe = GameDownloadRecovery.safeDestination(directory)
        if (this.directory != safe.path || this.branch != branch ||
            this.os != os || this.verify != verify) return false
        // A path alone cannot establish ownership of a partial installation.
        val marker = File(safe, ".cinderbox-download.session")
        return runCatching { marker.isFile && !Files.isSymbolicLink(marker.toPath()) &&
            marker.readText() == token }.getOrDefault(false)
    }
}

class GameDownloadRecovery(private val privateRoot: File) {
    private val journal get() = File(privateRoot, "m6-game-download.properties")

    companion object {
        private const val VERSION = "1"
        private const val APP_ID = "413150"

        /** Reject a symlink at any existing component, including ancestor folders. */
        fun safeDestination(directory: File): File {
            require(directory.isAbsolute) { "Game destination must be absolute" }
            var part: File? = directory.absoluteFile
            while (part != null) {
                require(!Files.isSymbolicLink(part.toPath())) { "Game directory contains a symbolic link" }
                part = part.parentFile
            }
            return directory.canonicalFile
        }
    }

    @Synchronized fun pending(): GameDownloadCheckpoint? {
        if (!journal.exists()) return null
        check(journal.isFile && journal.length() in 1..8192) { "Invalid interrupted download journal" }
        val props = Properties().apply { journal.inputStream().use { load(it) } }
        check(props.getProperty("schema") == VERSION && props.getProperty("app") == APP_ID) {
            "Unrecognized game download journal; refusing to continue"
        }
        val directory = props.getProperty("directory") ?: error("Missing download destination")
        val branch = props.getProperty("branch") ?: error("Missing Steam branch")
        val os = props.getProperty("os") ?: error("Missing target OS")
        val token = props.getProperty("token") ?: error("Missing session ownership marker")
        check(token.matches(Regex("[0-9a-f-]{36}"))) { "Invalid session marker" }
        val verify = when (props.getProperty("verify")) {
            "true" -> true
            "false" -> false
            else -> error("Invalid download verification preference")
        }
        check(branch.length in 1..128 && os in setOf("windows", "linux", "macos")) {
            "Invalid interrupted download options"
        }
        val safe = safeDestination(File(directory))
        check(safe.path == directory) { "Download path changed since checkpoint" }
        return GameDownloadCheckpoint(directory, branch, os, verify, token)
    }

    /** Only call this for a NEW, already preflighted empty installation directory. */
    @Synchronized fun beginNew(directory: File, branch: String, os: String, verify: Boolean) {
        check(pending() == null) { "Resolve the previous download before starting another" }
        val safe = safeDestination(directory)
        require(branch.length in 1..128 && os in setOf("windows", "linux", "macos")) {
            "Unsupported Steam download selection"
        }
        check(privateRoot.isDirectory || privateRoot.mkdirs()) { "App-private download storage inaccessible" }
        check(safe.isDirectory || safe.mkdirs()) { "Game download directory is inaccessible" }
        val token = UUID.randomUUID().toString()
        val marker = File(safe, ".cinderbox-download.session")
        check(marker.createNewFile()) { "Game directory already contains a download ownership marker" }
        try { marker.writeText(token) }
        catch (e: Exception) { marker.delete(); throw e }
        val props = Properties().apply {
            setProperty("schema", VERSION)
            setProperty("app", APP_ID)
            setProperty("directory", safe.path)
            setProperty("branch", branch)
            setProperty("os", os)
            setProperty("verify", verify.toString())
            setProperty("token", token)
        }
        val temp = File(privateRoot, "m6-game-download-${System.nanoTime()}.tmp")
        try {
            temp.outputStream().use { stream ->
                props.store(stream, "Interrupted game download checkpoint (no credentials)")
                stream.flush()
                if (stream is java.io.FileOutputStream) stream.fd.sync()
            }
            try {
                Files.move(temp.toPath(), journal.toPath(), StandardCopyOption.ATOMIC_MOVE)
            } catch (e: java.nio.file.AtomicMoveNotSupportedException) {
                Files.move(temp.toPath(), journal.toPath())
            }
        } catch (e: Exception) {
            // Failure before publishing a journal leaves no authorized resume session.
            if (!journal.exists()) marker.delete()
            throw e
        } finally {
            if (temp.exists()) temp.delete()
        }
    }

    @Synchronized fun requireMatching(directory: File, branch: String, os: String, verify: Boolean) {
        check(pending()?.matches(directory, branch, os, verify) == true) {
            "No matching interrupted download. Existing files will not be overwritten"
        }
    }

    /** A completed install is the ONLY automatic point where recovery is cleared. */
    @Synchronized fun completed() {
        val current = pending()
        if (current != null) {
            val marker = File(current.directory, ".cinderbox-download.session")
            if (marker.exists()) {
                check(!Files.isSymbolicLink(marker.toPath()) && marker.isFile &&
                    marker.readText() == current.token) { "Game download ownership changed" }
                check(marker.delete()) { "Cannot remove download ownership marker" }
            }
        }
        check(journal.delete() || !journal.exists()) { "Could not finalize download checkpoint" }
    }

    /** Explicit user discard; forgets the checkpoint but keeps game bytes. */
    @Synchronized fun discard() {
        val current = pending()
        if (current != null) {
            val marker = File(current.directory, ".cinderbox-download.session")
            if (marker.isFile && !Files.isSymbolicLink(marker.toPath()) &&
                runCatching { marker.readText() == current.token }.getOrDefault(false)) marker.delete()
        }
        check(journal.delete() || !journal.exists()) { "Cannot discard game download recovery journal" }
    }
}
