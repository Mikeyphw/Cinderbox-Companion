package com.sdvsync.mods

import android.content.Context
import com.sdvsync.BuildConfig
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.cinderbox.CinderboxPaths
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** LAB03A is synthetic-only. No Nexus authentication, network download, install or game mutation. */
internal object NexusLab03Evidence {
    private const val LAB_PACKAGE = "com.sdvsync.cbnx06lab"
    private const val SCOPE = "LAB_SYNTHETIC_ONLY"
    private const val FOLDER = "cbnx06-lab03-synthetic"
    data class Preview(val archiveSha256: String, val proposedChanges: Int, val archiveVerified: Boolean)

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }

    private fun archive(): ByteArray {
        val manifest = """{"Name":"CBNX06 LAB03 Synthetic","Author":"Cinderbox Test","Version":"1.0.0","UniqueID":"CBNX06.LAB03.Synthetic","Description":"Synthetic laboratory data only"}"""
        val output = ByteArrayOutputStream()
        ZipOutputStream(output).use { zip ->
            val entry = ZipEntry("CBNX06_LAB03_ONLY/manifest.json")
            entry.time = 0L
            zip.putNextEntry(entry)
            zip.write(manifest.toByteArray(Charsets.UTF_8))
            zip.closeEntry()
        }
        return output.toByteArray()
    }

    @Synchronized fun previewSynthetic(context: Context): Preview {
        check(BuildConfig.CBNX_LAB && context.packageName == LAB_PACKAGE) { "LAB03_NOT_ISOLATED_BUILD" }
        val directory = File(context.filesDir, FOLDER)
        CinderboxLabBoundary.requirePrivate(directory)
        check(directory.mkdirs() || directory.isDirectory) { "LAB03_PRIVATE_DIRECTORY_UNAVAILABLE" }
        check(!Files.isSymbolicLink(directory.toPath())) { "LAB03_LINKED_DIRECTORY" }
        val archiveFile = File(directory, "lab03-synthetic.zip")
        val receiptFile = File(directory, "lab03-synthetic-receipt.json")
        CinderboxLabBoundary.requirePrivate(archiveFile)
        CinderboxLabBoundary.requirePrivate(receiptFile)
        check(!Files.isSymbolicLink(archiveFile.toPath()) && !Files.isSymbolicLink(receiptFile.toPath())) {
            "LAB03_LINKED_EVIDENCE" }
        val expected = archive()
        check(expected.size in 128..16384) { "LAB03_ARCHIVE_BUDGET" }
        val digest = sha256(expected)
        if (archiveFile.exists()) {
            check(archiveFile.isFile && archiveFile.length() == expected.size.toLong() &&
                sha256(archiveFile.readBytes()) == digest) { "LAB03_ARCHIVE_CHANGED" }
        } else {
            val temporary = Files.createTempFile(directory.toPath(), "lab03-", ".tmp")
            try {
                CinderboxLabBoundary.requirePrivate(temporary.toFile())
                Files.write(temporary, expected)
                Files.move(temporary, archiveFile.toPath(), StandardCopyOption.ATOMIC_MOVE)
            } finally { Files.deleteIfExists(temporary) }
        }
        check(archiveFile.isFile && archiveFile.length() == expected.size.toLong() &&
            sha256(archiveFile.readBytes()) == digest) { "LAB03_ARCHIVE_DURABILITY_MISMATCH" }
        val mods = File(CinderboxPaths.MODS_DIR)
        CinderboxLabBoundary.requireModsRoot(mods)
        check(mods.isDirectory && !Files.isSymbolicLink(mods.toPath())) { "LAB03_MODS_NOT_PRIVATE" }
        // Observe only direct child metadata. Do not scan user game data or migrate legacy names.
        fun snapshot() = mods.listFiles()?.map { it.name to it.length() }?.sortedBy { it.first }
            ?: error("LAB03_MODS_UNAVAILABLE")
        val before = snapshot()
        val review = ModFileManager(context, ModManifestParser()).previewFromZip(archiveFile)
        val after = snapshot()
        check(before == after) { "LAB03_PREVIEW_MUTATED_MODS" }
        check(review.changes.size == 1) { "LAB03_AMBIGUOUS_PREVIEW" }
        val receipt = JSONObject().put("schema", "cbnx06-lab03-synthetic-v1")
            .put("scope", SCOPE).put("archive_sha256", digest)
            .put("proposed_changes", review.changes.size)
            .put("nexus_file_provenance_verified", false)
            .put("installed", false).put("production_files_examined", false)
            .toString()
        if (receiptFile.exists()) {
            check(receiptFile.isFile && receiptFile.length() in 1..4096 &&
                receiptFile.readText() == receipt) { "LAB03_RECEIPT_CHANGED" }
        } else {
            val temporary = Files.createTempFile(directory.toPath(), "lab03-receipt-", ".tmp")
            try {
                CinderboxLabBoundary.requirePrivate(temporary.toFile())
                Files.write(temporary, receipt.toByteArray(Charsets.UTF_8))
                Files.move(temporary, receiptFile.toPath(), StandardCopyOption.ATOMIC_MOVE)
            } finally { Files.deleteIfExists(temporary) }
        }
        check(receiptFile.isFile && receiptFile.readText() == receipt) { "LAB03_RECEIPT_DURABILITY_MISMATCH" }
        return Preview(digest, review.changes.size, true)
    }
}
