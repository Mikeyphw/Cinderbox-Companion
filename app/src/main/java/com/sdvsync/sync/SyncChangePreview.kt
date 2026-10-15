package com.sdvsync.sync

import java.security.MessageDigest

/** Read-only metadata comparison; neither previews nor their tokens authorize writes by themselves. */
enum class SyncPreviewDirection { PULL, PUSH }
enum class SyncPreviewAction { ADD, OVERWRITE, UNCHANGED, PRESERVE }

data class CloudFileStamp(val name: String, val size: Long, val sha1: String,
                          val timestamp: Long, val remoteIdentity: String)
data class SyncPreviewFile(val name: String, val action: SyncPreviewAction, val bytes: Long)
data class SyncChangePreview(
    val saveFolder: String,
    val direction: SyncPreviewDirection,
    val force: Boolean,
    val fingerprint: String,
    val files: List<SyncPreviewFile>,
    val warnings: List<String>
) {
    val writeCount: Int get() = files.count {
        it.action == SyncPreviewAction.ADD || it.action == SyncPreviewAction.OVERWRITE
    }
}

object SyncChangePreviewBuilder {
    private fun sha1(data: ByteArray): String = MessageDigest.getInstance("SHA-1")
        .digest(data).joinToString("") { "%02x".format(it) }
    private fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    private fun safeName(name: String): Boolean = name.isNotBlank() && name != "." &&
        name != ".." && '/' !in name && '\\' !in name && '\u0000' !in name

    fun build(saveFolder: String, direction: SyncPreviewDirection, force: Boolean,
              local: Map<String, ByteArray>, cloud: List<CloudFileStamp>): SyncChangePreview {
        require(safeName(saveFolder)) { "Unsafe save folder" }
        require(local.keys.all(::safeName) && cloud.all { safeName(it.name) }) {
            "Unsafe save filename; cannot preview"
        }
        require(cloud.map { it.name }.toSet().size == cloud.size) {
            "Duplicate cloud filenames; cannot preview"
        }
        require(cloud.all { it.size >= 0 && it.sha1.matches(Regex("[0-9a-fA-F]{40}")) }) {
            "Cloud file metadata incomplete; cannot preview"
        }
        require(if (direction == SyncPreviewDirection.PUSH) local.isNotEmpty() else cloud.isNotEmpty()) {
            "Selected sync source has no files"
        }
        val cloudByName = cloud.associateBy { it.name }
        val allNames = (local.keys + cloudByName.keys).toSortedSet()
        val fingerprintData = buildString {
            append(saveFolder).append('\u0000').append(direction.name).append('\u0000').append(force)
            for (name in allNames) {
                val localBytes = local[name]
                val remote = cloudByName[name]
                append('\n').append(name.length).append(':').append(name)
                append('|').append(localBytes?.size ?: -1).append('|')
                    .append(localBytes?.let(::sha1).orEmpty())
                append('|').append(remote?.size ?: -1).append('|')
                    .append(remote?.sha1?.lowercase().orEmpty())
                append('|').append(remote?.timestamp ?: -1)
                append('|').append(remote?.remoteIdentity.orEmpty())
            }
        }
        val files = allNames.map { name ->
            val l = local[name]
            val r = cloudByName[name]
            val action = when (direction) {
                SyncPreviewDirection.PUSH -> when {
                    l == null -> SyncPreviewAction.PRESERVE
                    r == null -> SyncPreviewAction.ADD
                    l.size.toLong() == r.size && sha1(l).equals(r.sha1, true) -> SyncPreviewAction.UNCHANGED
                    else -> SyncPreviewAction.OVERWRITE
                }
                SyncPreviewDirection.PULL -> when {
                    r == null -> SyncPreviewAction.PRESERVE
                    l == null -> SyncPreviewAction.ADD
                    l.size.toLong() == r.size && sha1(l).equals(r.sha1, true) -> SyncPreviewAction.UNCHANGED
                    else -> SyncPreviewAction.OVERWRITE
                }
            }
            SyncPreviewFile(name, action, if (direction == SyncPreviewDirection.PUSH)
                (l?.size?.toLong() ?: r?.size ?: 0) else (r?.size ?: l?.size?.toLong() ?: 0))
        }
        return SyncChangePreview(saveFolder, direction, force, sha256(fingerprintData), files,
            listOf("A preview is not a backup. Existing sync conflict and backup protections remain active.",
                "Files only present on the destination are preserved; no deletions are proposed.") +
                if (force) listOf("Force mode may overwrite a newer save; review carefully.") else emptyList())
    }
}
