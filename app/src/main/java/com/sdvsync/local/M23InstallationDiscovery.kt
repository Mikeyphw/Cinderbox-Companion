package com.sdvsync.local

import java.io.File
import java.nio.file.Files

/**
 * M23: bounded, read-only observation of specifically authorized direct filesystem paths.
 * Does not traverse children recursively or infer Steam entitlement/version from filenames.
 * SAF URI permissions and Root/Shizuku availability are NOT evidence of direct File access.
 */
object M23InstallationDiscovery {
    const val MAX_CHILDREN = 256
    enum class Status { MISSING, INACCESSIBLE, UNSAFE_LINK, PARTIAL, RECOVERY_REVIEW, CANDIDATE_UNVERIFIED, CONFLICT }
    enum class Layout { SELECTED, MODERN_08, LEGACY_PRE08, SMAPI }
    enum class Evidence { DIRECTORY_ONLY, CORE_FILES, CONTENT_ASSETS, LOCAL_MARKER_UNTRUSTED, UNTRUSTED_ARCHIVE, NONE }

    data class Finding(
        val layout: Layout,
        val status: Status,
        val codes: List<String>,
        val evidence: List<Evidence>,
        val observedFiles: Int = 0,
        val observedBytes: Long? = null,
        val version: String = "UNKNOWN_NO_AUTHENTICATED_MANIFEST",
        val verified: Boolean = false,
        val canInstallOrOverwrite: Boolean = false
    )

    data class Inventory(
        val selected: Finding,
        val modern: Finding,
        val legacy: Finding,
        val smapi: Finding,
        val storageAccess: String,
        val layoutConflict: Boolean,
        val gameAlreadyPresent: Boolean,
        val downloadAllowed: Boolean = false,
        val externalDeviceReadPerformed: Boolean = false,
        val writesPerformed: Boolean = false
    )

    private val dlls = listOf(
        "Stardew Valley.dll", "StardewValley.GameData.dll", "BmFont.dll",
        "xTile.dll", "Lidgren.Network.dll"
    )

    private fun linked(file: File): Boolean {
        var cursor: File? = file.absoluteFile
        while (cursor != null) {
            if (Files.isSymbolicLink(cursor.toPath())) return true
            cursor = cursor.parentFile
        }
        return false
    }

    private fun children(folder: File): List<File>? = try {
        // DirectoryStream stops after 257 entries; never materialize an unbounded listing.
        Files.newDirectoryStream(folder.toPath()).use { stream ->
            val result = ArrayList<File>()
            for (entry in stream) {
                if (result.size == MAX_CHILDREN) return null
                result += entry.toFile()
            }
            result
        }
    } catch (_: java.io.IOException) { null } catch (_: SecurityException) { null }

    private fun finding(layout: Layout, status: Status, vararg codes: String,
                        evidence: List<Evidence> = listOf(Evidence.NONE),
                        children: List<File> = emptyList()): Finding = Finding(
        layout, status, codes.toList(), evidence, children.size,
        null // Full installation size is unknown; no recursive size scan is permitted.
    )

    /** Only checks immediate children, known core game entries and known stage markers. */
    fun game(folder: File, layout: Layout = Layout.SELECTED): Finding {
        if (!folder.isAbsolute) return finding(layout, Status.INACCESSIBLE, "ABSOLUTE_PATH_REQUIRED")
        if (linked(folder)) return finding(layout, Status.UNSAFE_LINK, "SYMLINK_IN_PATH")
        if (!folder.exists()) {
            var parent = folder.parentFile
            while (parent != null && !parent.exists()) parent = parent.parentFile
            if (parent == null || !parent.isDirectory || !parent.canRead())
                return finding(layout, Status.INACCESSIBLE, "PARENT_ACCESS_NOT_CONFIRMED")
            return finding(layout, Status.MISSING, "PATH_MISSING")
        }
        if (!folder.isDirectory || !folder.canRead())
            return finding(layout, Status.INACCESSIBLE, "DIRECTORY_UNREADABLE")
        val listing = children(folder) ?: return finding(layout, Status.INACCESSIBLE, "DIRECTORY_UNREADABLE_OR_TOO_MANY_ENTRIES")
        if (listing.isEmpty()) return finding(layout, Status.MISSING, "EMPTY_DIRECTORY")
        if (listing.any { linked(it) }) return finding(layout, Status.UNSAFE_LINK, "SYMLINK_DIRECT_CHILD")
        val marker = File(folder, ".cinderbox-download.session")
        val staged = listing.any { it.name.startsWith(".sdvsync-stage-") || it.name == ".DepotDownloader" ||
            it.name.endsWith(".partial") || it.name.endsWith(".part") }
        val interrupted = marker.exists() || staged
        val archive = listing.any { it.isFile && it.length() > 0 &&
            (it.name.endsWith(".zip", true) || it.name.endsWith(".7z", true)) }
        val evidence = mutableListOf(Evidence.DIRECTORY_ONLY)
        if (marker.exists()) evidence += Evidence.LOCAL_MARKER_UNTRUSTED
        if (archive) evidence += Evidence.UNTRUSTED_ARCHIVE
        val content = File(folder, "Content")
        val contentList = if (content.isDirectory && !linked(content)) children(content) else null
        val core = dlls.all { name ->
            val f = File(folder, name)
            f.isFile && f.canRead() && !linked(f) && f.length() > 0L
        }
        if (core) evidence += Evidence.CORE_FILES
        if (contentList != null && contentList.isNotEmpty() && contentList.none { linked(it) })
            evidence += Evidence.CONTENT_ASSETS
        if ((content.exists() && linked(content)) || contentList?.any { linked(it) } == true)
            return finding(layout, Status.UNSAFE_LINK, "CONTENT_LINK", evidence = evidence, children = listing)
        if (interrupted) return finding(layout, Status.RECOVERY_REVIEW,
            "UNTRUSTED_DOWNLOAD_MARKER_OR_STAGE", evidence = evidence, children = listing)
        if (!core || contentList.isNullOrEmpty() || contentList.any { linked(it) }) {
            return finding(layout, Status.PARTIAL,
                if (archive) "UNVERIFIED_ARCHIVE_NOT_AN_INSTALL" else "REQUIRED_GAME_ASSETS_MISSING",
                evidence = evidence, children = listing)
        }
        return finding(layout, Status.CANDIDATE_UNVERIFIED,
            "NO_AUTHENTICATED_DEPOT_MANIFEST", "GAME_VERSION_UNKNOWN",
            evidence = evidence, children = listing)
    }

    fun smapi(folder: File): Finding {
        val layout = Layout.SMAPI
        if (!folder.isAbsolute) return finding(layout, Status.INACCESSIBLE, "ABSOLUTE_PATH_REQUIRED")
        if (linked(folder)) return finding(layout, Status.UNSAFE_LINK, "SYMLINK_IN_PATH")
        if (!folder.exists()) return finding(layout, Status.MISSING, "SMAPI_MISSING")
        if (!folder.isDirectory || !folder.canRead()) return finding(layout, Status.INACCESSIBLE, "SMAPI_UNREADABLE")
        val list = children(folder) ?: return finding(layout, Status.INACCESSIBLE, "SMAPI_UNREADABLE_OR_TOO_MANY_ENTRIES")
        if (list.any { linked(it) }) return finding(layout, Status.UNSAFE_LINK, "SMAPI_SYMLINK")
        if (list.isEmpty()) return finding(layout, Status.PARTIAL, "SMAPI_EMPTY")
        val parent = folder.parentFile
        if (list.any { it.name.startsWith(".sdvsync-stage-") } ||
            (parent != null && (File(parent, ".${folder.name}.sdvsync-stage").exists() ||
                File(parent, ".${folder.name}.sdvsync-backup").exists()))) {
            return finding(layout, Status.RECOVERY_REVIEW, "SMAPI_TRANSACTION_RECOVERY_REQUIRED", children = list)
        }
        val binary = list.any { it.isFile && it.length() > 0L &&
            (it.name.equals("SMAPI.dll", true) || it.name.equals("StardewModdingAPI.dll", true)) }
        return if (binary) finding(layout, Status.CANDIDATE_UNVERIFIED,
            "SMAPI_VERSION_AND_GAME_COMPATIBILITY_UNKNOWN", evidence = listOf(Evidence.CORE_FILES), children = list)
        else finding(layout, Status.PARTIAL, "SMAPI_BINARY_MISSING", children = list)
    }

    /** Read-only. Does not perform probe writes or traverse outside the explicit roots. */
    fun inspect(selected: File, installationRoot: File): Inventory {
        val modern = game(File(installationRoot, "desktop/GameFiles"), Layout.MODERN_08)
        val legacy = game(File(installationRoot, "GameFiles"), Layout.LEGACY_PRE08)
        // A single known Steam archive wrapper is safe to recognize; never recursively hunt.
        val wrapped = File(selected, "Stardew Valley")
        val selectedFinding = if (selected.isDirectory && !linked(selected) &&
            !File(selected, "Stardew Valley.dll").exists() && wrapped.isDirectory)
            game(wrapped) else game(selected)
        val smapiFinding = smapi(File(installationRoot, "smapi-internal"))
        val conflict = modern.status !in setOf(Status.MISSING, Status.INACCESSIBLE) &&
            legacy.status !in setOf(Status.MISSING, Status.INACCESSIBLE)
        val selectedAccess = when (selectedFinding.status) {
            Status.INACCESSIBLE, Status.UNSAFE_LINK -> "DIRECT_FILE_ACCESS_UNAVAILABLE"
            Status.MISSING -> "DIRECT_PATH_MISSING_WRITE_NOT_TESTED"
            else -> "DIRECT_FILE_READ_ONLY_OBSERVATION_WRITE_NOT_TESTED"
        }
        val anyGame = listOf(modern, legacy, selectedFinding).any { it.status in setOf(
            Status.PARTIAL, Status.RECOVERY_REVIEW, Status.CANDIDATE_UNVERIFIED, Status.CONFLICT) }
        return Inventory(selectedFinding, modern, legacy, smapiFinding, selectedAccess,
            conflict, anyGame)
    }
}
