package com.sdvsync.mods

import android.content.Context
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.models.InstallResult
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModProfile
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
    private val profileTransactions = ModProfileTransaction(context.filesDir, modsDir)
    private val batchTransactions = ModBatchTransaction(context.filesDir, modsDir)

    fun isModsDirAccessible(): Boolean = modsDir.exists() && modsDir.isDirectory && modsDir.canRead()

    fun listRetainedSnapshots(): List<ModSnapshot> = safety.list()

    @Synchronized fun restoreSnapshot(id: String): Boolean {
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
        return safety.restore(id)
    }

    /** A read-only review of all destination changes. ZIP extraction uses existing budgets. */
    @Synchronized fun previewFromZip(zipFile: File): ModArchivePreview {
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
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
            val sourceFolders = manifests.map { requireNotNull(it.parentFile).canonicalFile }
            check(sourceFolders.distinct().size == sourceFolders.size &&
                sourceFolders.none { parent -> sourceFolders.any { it != parent &&
                    it.path.startsWith(parent.path + File.separator) } }) {
                "Nested or repeated mod manifests in archive are ambiguous"
            }
            val changes = manifests.map { manifestFile ->
                val manifest = requireNotNull(parser.parse(manifestFile.readText())) { "Invalid mod manifest" }
                require(ids.add(manifest.uniqueID.lowercase(Locale.ROOT))) { "Duplicate mod ID in archive" }
                val source = requireNotNull(manifestFile.parentFile)
                val name = source.name.takeIf { it != temporary.name }
                    ?: manifest.name.replace(Regex("[^a-zA-Z0-9._\\- ]"), "")
                val matches = currentMods.filter { it.manifest.uniqueID.equals(manifest.uniqueID, true) }
                require(matches.size <= 1) { "Duplicate installed mod ID: ${manifest.uniqueID}" }
                val target = safeFolder(matches.singleOrNull()?.folderName ?: name)
                require(targets.add(target.name.lowercase(Locale.ROOT))) { "Conflicting destinations in archive" }
                check(!target.exists() || matches.isNotEmpty()) { "Different mod already occupies ${target.name}" }
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
            return ModArchivePreview(digest, changes,
                batchTransactions.destinationFingerprint(changes.map { it.folder }))
        } finally { temporary.deleteRecursively() }
    }

    /**
     * Scan the Mods/ directory and parse all installed mods.
     */
    @Synchronized fun listInstalledMods(): List<InstalledMod> {
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
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

    /** Journaled before the first rename; recovery reverses interrupted profile changes. */
    @Synchronized fun applyProfileSafely(profile: ModProfile, expectedFingerprint: String): Int {
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
        check(safety.recover()) { "An interrupted mod operation needs recovery" }
        val current = listInstalledMods()
        val preview = ModCompatibility.preview(current, profile)
        check(preview.fingerprint == expectedFingerprint) {
            "Mod folders changed since profile review. Please review again"
        }
        check(preview.blockers.isEmpty()) {
            preview.blockers.joinToString("; ") { it.message }
        }
        // Preflight the validated direct children, then journal before the first rename.
        for (step in preview.steps) {
            val from = safeFolder(step.fromFolder)
            val to = safeFolder(step.toFolder)
            check(from.isDirectory && !Files.isSymbolicLink(from.toPath()) && !to.exists()) {
                "Profile rename collision: ${step.name}"
            }
        }
        return profileTransactions.apply(preview.steps.map {
            ProfileFolderMove(it.fromFolder, it.toFolder)
        })
    }

    @Synchronized fun enableMod(folderName: String): Boolean {
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
        if (!folderName.startsWith(".")) return true
        return renameMod(folderName, folderName.removePrefix("."))
    }

    @Synchronized fun disableMod(folderName: String): Boolean {
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
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
        check(batchTransactions.recover()) { "Mod batch recovery requires manual inspection" }
        check(profileTransactions.recover()) { "Profile recovery needs manual review" }
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

    /** A multi-mod archive is one durable transaction, never a partially installed subset. */
    @Synchronized fun installFromZip(zipFile: File, approvedReviewKey: String): InstallResult {
        val tempDir = Files.createTempDirectory(context.cacheDir.toPath(), "m9_extract_").toFile()
        try {
            // The approval includes ZIP bytes, all target actions AND original folder bytes.
            val currentReview = previewFromZip(zipFile)
            check(currentReview.approvalKey == approvedReviewKey) {
                "Mod archive or installed files changed since review; review again"
            }
            extractZip(zipFile, tempDir)
            val manifestFiles = tempDir.walkTopDown().filter {
                it.isFile && it.name.equals("manifest.json", ignoreCase = true)
            }.toList()
            check(manifestFiles.isNotEmpty()) { "No mod manifests in archive" }
            val folders = manifestFiles.map { requireNotNull(it.parentFile).canonicalFile }
            check(folders.distinct().size == folders.size &&
                folders.none { parent -> folders.any { it != parent &&
                    it.path.startsWith(parent.path + File.separator) } }) {
                "Nested or duplicate mod manifests are not safe to install together"
            }
            val current = listInstalledMods()
            val seenIds = mutableSetOf<String>()
            val entries = manifestFiles.map { manifestFile ->
                val manifest = requireNotNull(parser.parse(manifestFile.readText())) {
                    "Invalid mod manifest"
                }
                check(seenIds.add(manifest.uniqueID.lowercase(Locale.ROOT))) {
                    "Duplicate mod identity in archive"
                }
                val existing = current.filter { it.manifest.uniqueID.equals(manifest.uniqueID, true) }
                check(existing.size <= 1) { "Duplicate installed mod identity" }
                val source = requireNotNull(manifestFile.parentFile)
                val folder = source.name.takeIf { it != tempDir.name }
                    ?: manifest.name.replace(Regex("[^a-zA-Z0-9._\\- ]"), "")
                val targetName = safeFolder(existing.singleOrNull()?.folderName ?: folder).name
                BatchModEntry(targetName, source)
            }
            // The second extraction must resolve exactly the same reviewed destinations.
            check(entries.map { it.targetName } == currentReview.changes.map { it.folder }) {
                "Archive destinations changed since review"
            }
            val count = batchTransactions.install(entries, snapshot = { target ->
                check(safety.snapshot(target) != null) { "Unable to retain pre-install mod snapshot" }
            }, expectedExistingDigest = currentReview.existingDigest)
            check(count == entries.size) { "Incomplete mod batch installation" }
            val installed = entries.mapNotNull { parseMod(safeFolder(it.targetName)) }
            AppLogger.i(TAG, "Installed mod archive as an atomic batch ($count mods)")
            return InstallResult.Success(installed)
        } catch (e: Exception) {
            AppLogger.e(TAG, "Atomic mod archive installation rejected", e)
            return InstallResult.Error(e.message ?: "Batch installation failed")
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
