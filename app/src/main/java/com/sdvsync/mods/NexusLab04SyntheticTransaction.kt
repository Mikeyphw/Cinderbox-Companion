package com.sdvsync.mods

import android.content.Context
import com.sdvsync.BuildConfig
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.mods.models.InstallResult
import org.json.JSONObject
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest

/**
 * LAB04 one-shot synthetic install and user-triggered rollback in the app-private LAB Mods root.
 * Uses the REAL ModFileManager preview/approved install and snapshot-backed remove operations.
 * Never reads a production root, starts a download, trusts browser requests, or installs live Nexus bytes.
 * Interrupted/corrupt state is intentionally NON-recoverable here: explicit operator review is required.
 */
internal object NexusLab04SyntheticTransaction {
    private const val APP = "com.sdvsync.cbnx06lab"
    private const val JOURNAL = "cbnx06-lab04-synthetic-transaction.json"
    private const val STAGE_FOLDER = "cbnx06-lab03d-staging"
    private const val MANIFEST = """{"Name":"CBNX06 LAB03 Synthetic","Author":"Cinderbox Test","Version":"1.0.0","UniqueID":"CBNX06.LAB03.Synthetic","Description":"Synthetic laboratory data only"}"""

    data class Evidence(val state: String, val sha256: String, val restoredEmptyRoot: Boolean)

    private fun sha(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }

    private fun checked(context: Context): Pair<File, File> {
        check(BuildConfig.CBNX_LAB && BuildConfig.APPLICATION_ID == APP &&
            context.packageName == APP) { "LAB04_NOT_ISOLATED_APP" }
        val mods = File(CinderboxPaths.MODS_DIR)
        CinderboxLabBoundary.requireModsRoot(mods)
        check(mods.isDirectory && !Files.isSymbolicLink(mods.toPath())) { "LAB04_MODS_UNSAFE" }
        val journal = File(context.filesDir.canonicalFile, JOURNAL)
        CinderboxLabBoundary.requirePrivate(journal)
        check(!Files.isSymbolicLink(journal.toPath())) { "LAB04_JOURNAL_SYMLINK" }
        return mods to journal
    }

    private fun rootMembers(mods: File): List<File> =
        requireNotNull(mods.listFiles()?.toList()) { "LAB04_ROOT_UNREADABLE" }.also { members ->
            check(members.none { Files.isSymbolicLink(it.toPath()) }) { "LAB04_LINKED_MOD" }
        }

    private fun stored(journal: File): JSONObject? {
        if (!journal.exists()) return null
        check(journal.isFile && journal.length() in 1L..2048L) { "LAB04_JOURNAL_INVALID_SIZE" }
        val data = JSONObject(journal.readText())
        check(data.length() == 8 && NexusLab04SyntheticPolicy.validReceipt(
            data.getString("schema"), data.getString("scope"),
            data.getString("source_provenance"), data.getString("archive_sha256"),
            data.getString("target_folder"), data.getString("state"),
            data.getBoolean("nexus_file_provenance_verified"),
            data.getBoolean("production_files_examined"))) { "LAB04_JOURNAL_INVALID" }
        return data
    }

    private fun persist(journal: File, previous: String?, next: String, digest: String) {
        check(NexusLab04SyntheticPolicy.allowedTransition(previous, next)) { "LAB04_TRANSITION_REFUSED" }
        val last = stored(journal)
        check(last?.getString("state") == previous &&
            (last == null || last.getString("archive_sha256") == digest)) { "LAB04_JOURNAL_RACE_OR_DRIFT" }
        val body = JSONObject()
            .put("schema", NexusLab04SyntheticPolicy.SCHEMA)
            .put("scope", NexusLab04SyntheticPolicy.SCOPE)
            .put("source_provenance", NexusLab04SyntheticPolicy.SOURCE)
            .put("archive_sha256", digest)
            .put("target_folder", NexusLab04SyntheticPolicy.FOLDER)
            .put("state", next)
            .put("nexus_file_provenance_verified", false)
            .put("production_files_examined", false)
            .toString().toByteArray(Charsets.UTF_8)
        val temp = Files.createTempFile(journal.parentFile.toPath(), "lab04-journal-", ".tmp")
        try {
            CinderboxLabBoundary.requirePrivate(temp.toFile())
            Files.write(temp, body)
            Files.move(temp, journal.toPath(), StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING)
        } finally { Files.deleteIfExists(temp) }
        check(stored(journal)?.getString("state") == next) { "LAB04_JOURNAL_NOT_DURABLE" }
    }

    private fun verifiedStagedArchive(context: Context): Pair<File, String> {
        // LAB03D re-verifies the app-private source and receipt, zip structure, SHA-256 and byte count.
        val receipt = NexusLab03DArchiveStage.stageSynthetic(context)
        check(receipt.provenance == NexusLab03DArchivePolicy.PROVENANCE) { "LAB04_NOT_LOCAL_SYNTHETIC" }
        val archive = File(File(context.filesDir.canonicalFile, STAGE_FOLDER),
            NexusLab04SyntheticPolicy.ARCHIVE_NAME)
        CinderboxLabBoundary.requirePrivate(archive)
        check(!Files.isSymbolicLink(archive.toPath()) && archive.isFile &&
            archive.length() == receipt.archiveBytes && archive.length() in 128L..16_384L &&
            sha(archive.readBytes()) == receipt.sha256) { "LAB04_STAGED_HASH_CHANGED" }
        return archive to receipt.sha256
    }

    private fun exactSyntheticMod(mods: File): Boolean {
        val folders = rootMembers(mods)
        if (folders.size != 1 || folders[0].name != NexusLab04SyntheticPolicy.FOLDER) return false
        val folder = folders.single()
        CinderboxLabBoundary.requirePrivate(folder)
        if (!folder.isDirectory || Files.isSymbolicLink(folder.toPath())) return false
        val children = requireNotNull(folder.listFiles()) { "LAB04_MOD_UNREADABLE" }
        if (children.size != 1 || children.single().name != "manifest.json") return false
        val manifest = children.single()
        CinderboxLabBoundary.requirePrivate(manifest)
        return manifest.isFile && !Files.isSymbolicLink(manifest.toPath()) &&
            manifest.length() in 1L..4096L && sha(manifest.readBytes()) == sha(MANIFEST.toByteArray(Charsets.UTF_8))
    }

    /** Initial install: empty private root, new transaction, exactly one reviewed synthetic ADD. */
    @Synchronized fun installSynthetic(context: Context): Evidence {
        val (mods, journal) = checked(context)
        check(NexusLab04SyntheticPolicy.mayInstall(stored(journal)?.getString("state"),
            rootMembers(mods).isEmpty())) { "LAB04_ALREADY_USED_OR_ROOT_NOT_EMPTY" }
        val (archive, hash) = verifiedStagedArchive(context)
        check(rootMembers(mods).isEmpty()) { "LAB04_ROOT_CHANGED_AFTER_STAGE" }
        val manager = ModFileManager(context, ModManifestParser())
        val review = manager.previewFromZip(archive)
        check(review.sha256 == hash && review.changes.size == 1 &&
            review.changes.single().action == "ADD" &&
            review.changes.single().folder == NexusLab04SyntheticPolicy.FOLDER &&
            review.changes.single().uniqueId == NexusLab04SyntheticPolicy.UNIQUE_ID) {
            "LAB04_NOT_EXACT_SYNTHETIC_ADD" }
        // Durable intent precedes ANY Mods writes; crashes stop automatically retrying.
        persist(journal, null, "INSTALLING", hash)
        val result = manager.installFromZip(archive, review.approvalKey)
        check(result is InstallResult.Success && result.mods.size == 1) { "LAB04_APPROVED_INSTALL_REFUSED" }
        check(exactSyntheticMod(mods)) { "LAB04_POST_INSTALL_BYTE_MISMATCH" }
        persist(journal, "INSTALLING", "INSTALLED", hash)
        return Evidence("INSTALLED", hash, false)
    }

    /** Explicit rollback: delete ONLY known synthetic folder via snapshot-retaining real manager path. */
    @Synchronized fun rollbackSynthetic(context: Context): Evidence {
        val (mods, journal) = checked(context)
        val receipt = requireNotNull(stored(journal)) { "LAB04_NO_INSTALL_RECEIPT" }
        val hash = receipt.getString("archive_sha256")
        check(NexusLab04SyntheticPolicy.mayRollback(receipt.getString("state"),
            exactSyntheticMod(mods))) { "LAB04_NOT_EXACT_UNMODIFIED_SYNTHETIC_INSTALL" }
        val (archive, digest) = verifiedStagedArchive(context)
        check(archive.isFile && digest == hash && exactSyntheticMod(mods)) {
            "LAB04_STAGED_OR_TARGET_DRIFT" }
        persist(journal, "INSTALLED", "ROLLING_BACK", hash)
        val manager = ModFileManager(context, ModManifestParser())
        check(manager.removeMod(NexusLab04SyntheticPolicy.FOLDER)) { "LAB04_SNAPSHOT_BACKED_REMOVE_REFUSED" }
        check(rootMembers(mods).isEmpty()) { "LAB04_ROOT_NOT_RESTORED_EMPTY" }
        persist(journal, "ROLLING_BACK", "ROLLED_BACK", hash)
        return Evidence("ROLLED_BACK", hash, true)
    }
}
