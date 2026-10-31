package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import java.security.MessageDigest

/** Independent byte comparison against file hashes supplied by a depot manifest.
 * This does NOT authenticate the origin/signature of the manifest itself.
 */
object M24DepotFileProof {
    data class FileEntry(val size: Long, val sha1: String)
    data class Result(val files: Int, val bytes: Long, val scope: String = "DEPOT_MANIFEST_SHA1_MATCH_UNSIGNED")
    private val hashPattern = Regex("[0-9a-f]{40}")

    fun checkedPath(path: String): String {
        val normalized = path.replace('\\', '/')
        require(normalized == path || !path.contains('/')) { "Ambiguous manifest path separators" }
        require(!normalized.startsWith('/') && !normalized.startsWith('~') &&
            !normalized.contains(':') && !normalized.contains('\u0000') &&
            normalized.split('/').none { it.isBlank() || it == "." || it == ".." }) {
            "Unsafe depot manifest path"
        }
        require(normalized.length <= 1024 && normalized.isNotEmpty()) { "Invalid manifest filename" }
        return normalized
    }

    /** Strict expected set, excluding only the SDK's own metadata directory.
     * No preexisting Cinderbox or outside directory is ever an input to this function.
     */
    fun verify(stage: File, expected: Map<String, FileEntry>,
               progress: (Int, Int) -> Unit = { _, _ -> }): Result {
        require(stage.isDirectory && !Files.isSymbolicLink(stage.toPath())) { "Owned stage missing or linked" }
        require(expected.isNotEmpty() && expected.size <= 100000) { "No bounded depot file list" }
        val canonical = stage.canonicalFile
        val seen = HashSet<String>()
        var total = 0L
        expected.entries.forEachIndexed { index, (path, entry) ->
            require(checkedPath(path) == path && entry.size >= 0 && hashPattern.matches(entry.sha1)) {
                "Untrusted depot file entry"
            }
            require(seen.add(path)) { "Duplicate depot file" }
            val file = File(stage, path)
            require(file.canonicalFile.toPath().startsWith(canonical.toPath())) { "Stage path escape" }
            var node: File? = file
            while (node != null && node.canonicalPath.startsWith(canonical.path)) {
                require(!Files.isSymbolicLink(node.toPath())) { "Linked depot path" }
                if (node == stage) break
                node = node.parentFile
            }
            check(file.isFile && file.length() == entry.size) { "Manifest size or file mismatch" }
            val hash = MessageDigest.getInstance("SHA-1")
            file.inputStream().buffered().use { input ->
                val chunk = ByteArray(65536)
                while (true) {
                    val count = input.read(chunk)
                    if (count == -1) break
                    hash.update(chunk, 0, count)
                }
            }
            val observed = hash.digest().joinToString("") { "%02x".format(it) }
            check(observed == entry.sha1) { "Depot manifest hash mismatch" }
            total = Math.addExact(total, entry.size)
            progress(index + 1, expected.size)
        }
        val disk = stage.walkTopDown().onEnter { directory ->
            require(!Files.isSymbolicLink(directory.toPath())) { "Linked staging directory" }
            directory == stage || directory.name != ".DepotDownloader"
        }.filter { file ->
            require(!Files.isSymbolicLink(file.toPath())) { "Linked staging file" }
            file.isFile && file.name != ".cinderbox-download.session"
        }.map { it.relativeTo(stage).invariantSeparatorsPath }.toSet()
        check(disk == expected.keys) { "Missing or unlisted staged files" }
        return Result(expected.size, total)
    }
}
