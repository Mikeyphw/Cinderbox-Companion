package com.sdvsync.mods

import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import java.util.Properties

/** Independent read-only app-private archive-vs-receipt proof; no provider authority. */
internal object NexusArchiveProvenance {
    private const val MAX_ARCHIVES = 24
    private const val MAX_TOTAL_BYTES = 1_073_741_824L
    private const val MAX_RECEIPT_BYTES = 32768L
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    private val jobId = Regex("[0-9a-fA-F-]{36}")
    private val digestPattern = Regex("[0-9a-f]{64}")
    data class Evidence(val available: Boolean, val confirmedJobIds: Set<String>)

    fun inspect(records: List<ModDownloadRecord>, root: File?): Evidence {
        if (root == null) return Evidence(false, emptySet())
        return try { scan(records, root) } catch (_: Exception) { Evidence(false, emptySet()) }
    }
    private fun scan(records: List<ModDownloadRecord>, root: File): Evidence {
        if (Files.isSymbolicLink(root.toPath()) || !root.isDirectory || !root.canRead()) return Evidence(false, emptySet())
        val head = File(root, "mod-review-pending.zip")
        val headProps = File(root, "mod-review-pending.properties")
        val backlog = File(root, "mod-review-backlog")
        if (head.exists() != headProps.exists()) return Evidence(false, emptySet())
        val pairs = mutableListOf<Pair<File, File>>()
        if (head.exists()) pairs += head to headProps
        if (backlog.exists()) {
            if (Files.isSymbolicLink(backlog.toPath()) || !backlog.isDirectory) return Evidence(false, emptySet())
            val children = backlog.listFiles() ?: return Evidence(false, emptySet())
            if (children.size > MAX_ARCHIVES * 2) return Evidence(false, emptySet())
            for (entry in children) {
                if (Files.isSymbolicLink(entry.toPath()) || !entry.isFile ||
                    !(entry.name.endsWith(".zip") || entry.name.endsWith(".properties")) ||
                    entry.name.startsWith(".")) return Evidence(false, emptySet())
            }
            val zips = children.filter { it.name.endsWith(".zip") }
            val props = children.filter { it.name.endsWith(".properties") }
            if (zips.size != props.size) return Evidence(false, emptySet())
            for (archive in zips) {
                val properties = File(backlog, archive.name.removeSuffix(".zip") + ".properties")
                if (!properties.isFile) return Evidence(false, emptySet())
                pairs += archive to properties
            }
        }
        if (pairs.size > MAX_ARCHIVES) return Evidence(false, emptySet())
        val known = records.associateBy { it.id }
        val confirmed = mutableSetOf<String>()
        var totalBytes = 0L
        for ((archive, propsFile) in pairs) {
            if (Files.isSymbolicLink(archive.toPath()) || Files.isSymbolicLink(propsFile.toPath()) ||
                !archive.isFile || !propsFile.isFile || !archive.canRead() || !propsFile.canRead() ||
                propsFile.length() !in 1..MAX_RECEIPT_BYTES) return Evidence(false, emptySet())
            val props = Properties().apply { propsFile.inputStream().use { load(it) } }
            val source = props.getProperty("source") ?: return Evidence(false, emptySet())
            if (source != "nexus") continue
            val id = props.getProperty("job_id") ?: return Evidence(false, emptySet())
            val mod = props.getProperty("mod_id") ?: return Evidence(false, emptySet())
            val file = props.getProperty("file_id") ?: return Evidence(false, emptySet())
            val expected = props.getProperty("sha256") ?: return Evidence(false, emptySet())
            if (!jobId.matches(id) || !positiveId.matches(mod) || !positiveId.matches(file) ||
                !digestPattern.matches(expected)) return Evidence(false, emptySet())
            val record = known[id] ?: return Evidence(false, emptySet())
            if (record.source != "nexus" || record.modId != mod || record.fileId != file ||
                record.status !in setOf("VALIDATING", "REVIEW_REQUIRED", "BLOCKED", "INSTALLING",
                    "INSTALLED", "VERIFY_REQUIRED")) return Evidence(false, emptySet())
            if (!confirmed.add(id)) return Evidence(false, emptySet())
            val originalLength = archive.length()
            val modifiedAt = archive.lastModified()
            if (originalLength !in 1..MAX_TOTAL_BYTES || totalBytes > MAX_TOTAL_BYTES - originalLength) return Evidence(false, emptySet())
            totalBytes += originalLength
            val hash = MessageDigest.getInstance("SHA-256")
            var received = 0L
            archive.inputStream().buffered().use { input ->
                val buffer = ByteArray(65536)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    received += count
                    if (received > originalLength) return Evidence(false, emptySet())
                    hash.update(buffer, 0, count)
                }
            }
            val actual = hash.digest().joinToString("") { "%02x".format(it) }
            if (actual != expected || received != originalLength ||
                archive.length() != originalLength || archive.lastModified() != modifiedAt ||
                !propsFile.isFile) return Evidence(false, emptySet())
        }
        return Evidence(true, confirmed)
    }
}
