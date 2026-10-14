package com.sdvsync.mods

import android.content.Context
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.models.InstallResult
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.util.ZipBudget
import java.io.File
import java.nio.file.Files
import java.util.Locale
import java.util.UUID
import java.util.zip.ZipInputStream

/**
 * Manages local mod files in the Mods/ directory.
 * Uses direct java.io.File access (Mods/ is on shared storage, not inside /Android/data/).
 */
class ModFileManager(
    private val context: Context,
    private val parser: ModManifestParser,
    private val modsDir: File = File(CinderboxPaths.MODS_DIR)
) {
    companion object {
        private const val TAG = "ModFileManager"
        private const val DISABLED_SUFFIX = ".disabled"
    }

    private val safety = ModSafety(context.filesDir, modsDir)

    fun isModsDirAccessible(): Boolean = modsDir.exists() && modsDir.isDirectory && modsDir.canRead()

    fun listRetainedSnapshots(): List<ModSnapshot> = safety.list()

    @Synchronized fun restoreSnapshot(id: String): Boolean = safety.restore(id)

    /** A read-only review of all destination changes. ZIP extraction uses existing budgets. */
    fun previewFromZip(zipFile: File): ModArchivePreview {
        check(safety.recover()) { "An interrupted mod operation needs manual recovery" }
        val digest = safety.digest(zipFile)
        val temporary = Files.createTempDirectory(context.cacheDir.toPath(), "mod_preview_").toFile()
        try {
            extractZip(zipFile, temporary)
            val manifests = temporary.walkTopDown().filter { it.isFile &&
                it.name.equals("manifest.json", ignoreCase = true) }.toList()
            require(manifests.isNotEmpty()) { "No mod manifests in archive" }
            // A preview must never rename legacy disabled folders.
            val currentMods = modsDir.listFiles()?.filter { it.isDirectory }
                ?.mapNotNull { parseMod(it) } ?: emptyList()
            val ids = mutableSetOf<String>()
            val targets = mutableSetOf<String>()
            val changes = manifests.map { manifestFile ->
                val manifest = requireNotNull(parser.parse(manifestFile.readText())) { "Invalid mod manifest" }
                require(ids.add(manifest.uniqueID.lowercase(Locale.ROOT))) { "Duplicate mod ID in archive" }
                val source = requireNotNull(manifestFile.parentFile)
                val name = source.name.takeIf { it != temporary.name }
                    ?: manifest.name.replace(Regex("[^a-zA-Z0-9._\\- ]"), "")
                val existing = currentMods.firstOrNull { it.manifest.uniqueID.equals(manifest.uniqueID, true) }
                val target = safeFolder(existing?.folderName ?: name)
                require(targets.add(target.name.lowercase(Locale.ROOT))) { "Conflicting destinations in archive" }
                check(!target.exists() || existing != null) { "Different mod already occupies ${target.name}" }
                check(!target.exists() || target.isDirectory) { "Invalid existing mod directory" }
                // Do not follow symbolic links inside the target or inside staging.
                val original = if (target.isDirectory) target.walkTopDown().filter { it.isFile }.map {
                    require(!Files.isSymbolicLink(it.toPath())) { "Mod contains a symlink" }
                    it.relativeTo(target).invariantSeparatorsPath
                }.toSet() else emptySet()
                val incoming = source.walkTopDown().filter { it.isFile }.map {
                    require(!Files.isSymbolicLink(it.toPath())) { "Archive contains a symlink" }
                    it.relativeTo(source).invariantSeparatorsPath
                }.toSet()
                val preserved = setOf("config.json")
                ModReviewChange(manifest.name, manifest.uniqueID, target.name,
                    if (target.exists()) "REPLACE" else "ADD",
                    (incoming - original).size, (incoming intersect original).size,
                    ((original - incoming) - preserved).size)
            }
            return ModArchivePreview(digest, changes)
        } finally { temporary.deleteRecursively() }
    }

    /**
     * Scan the Mods/ directory and parse all installed mods.
     */
    fun listInstalledMods(): List<InstalledMod> {
        if (!modsDir.exists()) return emptyList()

        return modsDir.listFiles()
            ?.filter { it.isDirectory }
            ?.mapNotNull { folder ->
                val normalized = if (folder.name.endsWith(DISABLED_SUFFIX) &&
                    !folder.name.startsWith(".") &&
                    File(folder, "manifest.json").isFile
                ) {
                    val target = File(modsDir, ".${folder.name.removeSuffix(DISABLED_SUFFIX)}")
                    if (!target.exists() && folder.renameTo(target)) target else folder
                } else {
                    folder
                }
                parseMod(normalized)
            }
            ?.sortedBy { it.manifest.name.lowercase() }
            ?: emptyList()
    }

    private fun parseMod(folder: File): InstalledMod? {
        val manifestFile = File(folder, "manifest.json")
        if (!manifestFile.exists()) return null

        val manifest = try {
            parser.parse(manifestFile.readText())
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to read manifest in ${folder.name}", e)
            null
        } ?: return null

        val enabled = !folder.name.startsWith(".")
        val folderSize = folder.walk().filter { it.isFile }.sumOf { it.length() }

        return InstalledMod(
            manifest = manifest,
            folderName = folder.name,
            folderPath = folder.absolutePath,
            enabled = enabled,
            installedAt = manifestFile.lastModified(),
            fileSize = folderSize
        )
    }

    fun enableMod(folderName: String): Boolean {
        if (!folderName.startsWith(".")) return true
        return renameMod(folderName, folderName.removePrefix("."))
    }

    fun disableMod(folderName: String): Boolean {
        if (folderName.startsWith(".")) return true
        // SMAPI only skips folders whose names start with a dot.
        return renameMod(folderName, ".$folderName")
    }

    /** A mod operation must never escape Mods/ through ../ or a symlink. */
    private fun safeFolder(name: String): File {
        require(name.isNotBlank() && name != "." && name != ".." &&
            '/' !in name && '\\' !in name && '\u0000' !in name) { "Invalid mod folder name" }
        val folder = File(modsDir, name)
        require(folder.canonicalFile.parentFile == modsDir.canonicalFile) {
            "Mod path is outside the Mods directory"
        }
        return folder
    }

    private fun renameMod(from: String, to: String): Boolean {
        val target = safeFolder(to)
        if (target.exists()) return false
        return safeFolder(from).renameTo(target)
    }

    /** Remove one validated direct child, never an arbitrary path. */
    @Synchronized fun removeMod(folderName: String): Boolean {
        val folder = safeFolder(folderName)
        check(safety.recover()) { "An interrupted mod transaction needs recovery" }
        if (!folder.exists()) return true
        val snapshot = requireNotNull(safety.snapshot(folder)) { "Cannot snapshot mod before removal" }
        val held = File(modsDir, ".m5-delete-${UUID.randomUUID()}")
        safety.begin(folderName, snapshot, "remove")
        try {
            check(folder.renameTo(held)) { "Cannot stage mod removal" }
            check(held.deleteRecursively()) { "Could not finish mod removal" }
            safety.complete()
            AppLogger.i(TAG, "Removed $folderName; retained snapshot ${snapshot.id}")
            return true
        } catch (failure: Exception) {
            if (!folder.exists() && held.exists()) held.renameTo(folder)
            throw failure
        }
    }

    /**
     * Install a mod from a zip file.
     * Handles single-mod, nested-folder, and multi-mod archives.
     */
    /** Legacy callers are fail-closed: installation always requires a matching review key. */
    @Deprecated("Use previewFromZip then approved install")
    fun installFromZip(zipFile: File): InstallResult = InstallResult.Error("Preview and confirm the archive in Mods first")

    @Synchronized fun installFromZip(zipFile: File, approvedReviewKey: String): InstallResult {
        // Re-scan destinations immediately before mutation to reject stale previews.
        val currentReview = previewFromZip(zipFile)
        check(currentReview.approvalKey == approvedReviewKey) { "Mod archive or installed files changed since review" }
        val tempDir = Files.createTempDirectory(context.cacheDir.toPath(), "mod_extract_").toFile()
        try {
            // Extract zip to temp directory
            tempDir.mkdirs()
            extractZip(zipFile, tempDir)

            // Find all manifest.json files
            val manifests = tempDir.walk()
                .filter { it.name.equals("manifest.json", ignoreCase = true) && it.isFile }
                .toList()

            if (manifests.isEmpty()) {
                return InstallResult.Error("No manifest.json found in archive")
            }

            val installed = mutableListOf<InstalledMod>()

            for (manifestFile in manifests) {
                val modFolder = manifestFile.parentFile ?: continue
                val manifest = parser.parse(manifestFile.readText()) ?: continue

                // Determine the target folder name
                val targetName = modFolder.name.takeIf { it != tempDir.name }
                    ?: manifest.name.replace(Regex("[^a-zA-Z0-9._\\- ]"), "")

                require(targetName.isNotBlank() && targetName != "." && targetName != "..") {
                    "Invalid mod folder name"
                }
                val existing = modsDir.listFiles()?.filter { it.isDirectory }
                    ?.mapNotNull { parseMod(it) }?.firstOrNull {
                        it.manifest.uniqueID.equals(manifest.uniqueID, ignoreCase = true)
                    }
                val targetDir = safeFolder(existing?.folderName ?: targetName)
                check(!targetDir.exists() || existing != null) { "A different mod already uses $targetName" }
                Files.createDirectories(modsDir.toPath())
                val staged = Files.createTempDirectory(modsDir.toPath(), ".install-").toFile()
                val previous = File(modsDir, ".m5-hold-${UUID.randomUUID()}")
                val snapshot = safety.snapshot(targetDir)
                safety.begin(targetDir.name, snapshot, "install")
                try {
                    check(modFolder.copyRecursively(staged, overwrite = true)) { "Could not stage mod files" }
                    val config = File(targetDir, "config.json")
                    if (config.isFile) config.copyTo(File(staged, "config.json"), overwrite = true)
                    if (targetDir.exists()) Files.move(targetDir.toPath(), previous.toPath())
                    try {
                        Files.move(staged.toPath(), targetDir.toPath())
                    } catch (e: Exception) {
                        if (previous.exists()) Files.move(previous.toPath(), targetDir.toPath())
                        throw e
                    }
                    safety.complete()
                    if (previous.exists()) previous.deleteRecursively()
                } finally {
                    staged.deleteRecursively()
                }

                parseMod(targetDir)?.let { installed.add(it) }
                AppLogger.d(TAG, "Installed mod: ${manifest.name} to ${targetDir.name}")
            }

            return if (installed.isEmpty()) {
                InstallResult.Error("Failed to install any mods from archive")
            } else {
                InstallResult.Success(installed)
            }
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to install from zip", e)
            return InstallResult.Error(e.message ?: "Unknown error")
        } finally {
            tempDir.deleteRecursively()
        }
    }

    private fun extractZip(zipFile: File, destDir: File) {
        // 3,000 files, 128 MiB per entry, 1 GiB total uncompressed.
        val budget = ZipBudget(3_000, 128L * 1024 * 1024, 1024L * 1024 * 1024)
        ZipInputStream(zipFile.inputStream().buffered()).use { zip ->
            var entry = zip.nextEntry
            while (entry != null) {
                budget.nextEntry()
                val file = File(destDir, entry.name)
                if (!file.canonicalPath.startsWith(destDir.canonicalPath + File.separator)) {
                    throw SecurityException("Zip entry outside target dir: ${entry.name}")
                }
                if (entry.isDirectory) {
                    file.mkdirs()
                } else {
                    file.parentFile?.mkdirs()
                    file.outputStream().buffered().use { out ->
                        budget.copyEntry(zip, out)
                    }
                }
                zip.closeEntry()
                entry = zip.nextEntry
            }
        }
    }
}
