package com.sdvsync.mods

import android.content.Context
import com.sdvsync.BuildConfig
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.cinderbox.CinderboxPaths
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/** LAB03D: user-triggered synthetic-only archive staging. No Nexus bytes or installed-mod writes. */
internal object NexusLab03DArchiveStage {
    private const val APP = "com.sdvsync.cbnx06lab"
    private const val SOURCE_FOLDER = "cbnx06-lab03-synthetic"
    private const val STAGE_FOLDER = "cbnx06-lab03d-staging"
    private const val ARCHIVE_FILE = "lab03-synthetic.zip"
    private const val SOURCE_RECEIPT = "lab03-synthetic-receipt.json"
    private const val STAGED_RECEIPT = "lab03d-staged-receipt.json"

    data class Evidence(val sha256: String, val archiveBytes: Long, val provenance: String)

    private fun digest(file: File): String {
        val hasher = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(4096)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                if (count > 0) hasher.update(buffer, 0, count)
            }
        }
        return hasher.digest().joinToString("") { "%02x".format(it) }
    }

    private fun privateFile(file: File) {
        CinderboxLabBoundary.requirePrivate(file)
        check(!Files.isSymbolicLink(file.toPath())) { "LAB03D_SYMLINK_REFUSED" }
    }

    private fun inspectZip(source: File) {
        ZipInputStream(FileInputStream(source)).use { zip ->
            val entry = requireNotNull(zip.nextEntry) { "LAB03D_EMPTY_ZIP" }
            check(!entry.isDirectory && entry.name == NexusLab03DArchivePolicy.ENTRY) {
                "LAB03D_UNEXPECTED_ZIP_ENTRY"
            }
            val out = ByteArray(4097)
            var count = 0
            while (true) {
                val got = zip.read(out, count, out.size - count)
                if (got < 0) break
                count += got
                check(count < out.size) { "LAB03D_ZIP_ENTRY_TOO_LARGE" }
            }
            val manifest = JSONObject(String(out, 0, count, Charsets.UTF_8))
            check(manifest.getString("UniqueID") == "CBNX06.LAB03.Synthetic" &&
                manifest.getString("Version") == "1.0.0") { "LAB03D_NOT_SYNTHETIC_MANIFEST" }
            zip.closeEntry()
            check(zip.nextEntry == null) { "LAB03D_MULTIPLE_ZIP_ENTRIES" }
        }
    }

    private fun atomicWrite(dir: File, destination: File, bytes: ByteArray, prefix: String) {
        check(!destination.exists()) { "LAB03D_DESTINATION_ALREADY_EXISTS" }
        val temp = Files.createTempFile(dir.toPath(), prefix, ".tmp")
        try {
            privateFile(temp.toFile())
            Files.write(temp, bytes)
            // Never replace an existing receipt/archive; interruptions fail closed.
            Files.move(temp, destination.toPath(), StandardCopyOption.ATOMIC_MOVE)
        } finally {
            Files.deleteIfExists(temp)
        }
    }

    /** A second explicit LAB button, never a remote/browser-created staging capability. */
    @Synchronized fun stageSynthetic(context: Context): Evidence {
        check(BuildConfig.CBNX_LAB && BuildConfig.APPLICATION_ID == APP &&
            context.packageName == APP) { "LAB03D_NOT_ISOLATED_BUILD" }
        val mods = File(CinderboxPaths.MODS_DIR)
        CinderboxLabBoundary.requireModsRoot(mods)
        check(mods.isDirectory && !Files.isSymbolicLink(mods.toPath())) { "LAB03D_MODS_ROOT_UNSAFE" }
        fun snapshot() = requireNotNull(mods.listFiles()) { "LAB03D_MODS_UNAVAILABLE" }
            .map { Triple(it.name, it.length(), it.isDirectory) }.sortedBy { it.first }
        val before = snapshot()
        val preview = NexusLab03Evidence.previewSynthetic(context)
        check(preview.archiveVerified && preview.proposedChanges == 1) { "LAB03D_SOURCE_PREVIEW_NOT_VERIFIED" }
        val sourceDir = File(context.filesDir.canonicalFile, SOURCE_FOLDER)
        val stageDir = File(context.filesDir.canonicalFile, STAGE_FOLDER)
        for (dir in listOf(sourceDir, stageDir)) {
            privateFile(dir)
            check(dir.mkdirs() || dir.isDirectory) { "LAB03D_PRIVATE_DIRECTORY_UNAVAILABLE" }
        }
        val source = File(sourceDir, ARCHIVE_FILE)
        val sourceReceipt = File(sourceDir, SOURCE_RECEIPT)
        val stage = File(stageDir, ARCHIVE_FILE)
        val receipt = File(stageDir, STAGED_RECEIPT)
        for (file in listOf(source, sourceReceipt, stage, receipt)) privateFile(file)
        check(source.isFile && sourceReceipt.isFile &&
            source.length() in NexusLab03DArchivePolicy.MIN_ARCHIVE_BYTES..NexusLab03DArchivePolicy.MAX_ARCHIVE_BYTES &&
            sourceReceipt.length() in 1L..4096L) { "LAB03D_SOURCE_MISSING_OR_OVERSIZED" }
        val sourceHash = digest(source)
        check(sourceHash == preview.archiveSha256) { "LAB03D_SOURCE_DIGEST_MISMATCH" }
        val previous = JSONObject(sourceReceipt.readText())
        check(previous.getString("schema") == NexusLab03DArchivePolicy.SOURCE_SCHEMA &&
            previous.getString("scope") == NexusLab03DArchivePolicy.SCOPE &&
            previous.getString("archive_sha256") == sourceHash &&
            previous.getInt("proposed_changes") == 1 &&
            !previous.getBoolean("nexus_file_provenance_verified") &&
            !previous.getBoolean("installed") &&
            !previous.getBoolean("production_files_examined")) { "LAB03D_SOURCE_RECEIPT_UNTRUSTWORTHY" }
        inspectZip(source)
        // Both files must exist together on replay; a crash leaves incomplete state refused.
        check(stage.exists() == receipt.exists()) { "LAB03D_PARTIAL_STAGE_REFUSED" }
        if (!stage.exists()) {
            atomicWrite(stageDir, stage, source.readBytes(), "lab03d-archive-")
            privateFile(stage)
            check(stage.isFile && stage.length() == source.length() && digest(stage) == sourceHash) {
                "LAB03D_POST_COPY_DIGEST_MISMATCH" }
            val record = JSONObject()
                .put("schema", NexusLab03DArchivePolicy.STAGE_SCHEMA)
                .put("scope", NexusLab03DArchivePolicy.SCOPE)
                .put("source_provenance", NexusLab03DArchivePolicy.PROVENANCE)
                .put("source_sha256", sourceHash).put("staged_sha256", sourceHash)
                .put("source_bytes", source.length()).put("staged_bytes", stage.length())
                .put("nexus_file_provenance_verified", false)
                .put("installed", false).put("production_files_examined", false)
                .toString().toByteArray(Charsets.UTF_8)
            atomicWrite(stageDir, receipt, record, "lab03d-receipt-")
        }
        check(stage.isFile && receipt.isFile && receipt.length() in 1L..4096L) {
            "LAB03D_STAGE_MISSING_OR_UNSAFE" }
        val saved = JSONObject(receipt.readText())
        check(NexusLab03DArchivePolicy.validLocalReceipt(
            saved.getString("schema"), saved.getString("scope"),
            saved.getString("source_sha256"), saved.getString("staged_sha256"),
            saved.getLong("source_bytes"), saved.getLong("staged_bytes"),
            saved.getString("source_provenance"),
            saved.getBoolean("nexus_file_provenance_verified"), saved.getBoolean("installed"),
            saved.getBoolean("production_files_examined"))) { "LAB03D_STAGE_RECEIPT_INVALID" }
        check(stage.length() == source.length() &&
            saved.getLong("source_bytes") == source.length() &&
            saved.getString("source_sha256") == sourceHash &&
            digest(stage) == sourceHash) { "LAB03D_STAGE_CHANGED" }
        inspectZip(stage)
        check(before == snapshot()) { "LAB03D_MODS_CHANGED" }
        return Evidence(sourceHash, stage.length(), NexusLab03DArchivePolicy.PROVENANCE)
    }
}
