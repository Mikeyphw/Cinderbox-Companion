package com.sdvsync.download

import com.sdvsync.util.ZipBudget
import java.io.File
import java.io.FilterInputStream
import java.nio.file.Files
import java.util.Locale
import java.util.zip.ZipInputStream

/** Prepare a full SMAPI tree off to the side and swap it in by same-directory rename. */
object SmapiTransactionalInstaller {
    private const val MAX_ENTRIES = 8000
    private const val MAX_SINGLE_BYTES = 128L * 1024 * 1024
    private const val MAX_TOTAL_BYTES = 512L * 1024 * 1024
    private const val OWNED = ".sdvsync-stage-owned"
    private const val READY = ".sdvsync-stage-ready"

    private fun stage(destination: File) = File(destination.parentFile, ".${destination.name}.sdvsync-stage")
    private fun backup(destination: File) = File(destination.parentFile, ".${destination.name}.sdvsync-backup")

    private fun noSymlink(file: File) {
        require(!Files.isSymbolicLink(file.toPath())) { "Symlink in SMAPI transaction path: ${file.name}" }
    }

    /** Recover a crash after moving the old target aside or after promotion. */
    fun recover(destination: File) {
        noSymlink(destination)
        val pending = stage(destination)
        val previous = backup(destination)
        noSymlink(pending)
        noSymlink(previous)
        if (previous.exists()) {
            require(previous.isDirectory) { "SMAPI backup is not a directory" }
            if (!destination.exists()) {
                check(previous.renameTo(destination)) { "Could not restore interrupted SMAPI update" }
            } else {
                // Promotion finished and left its ready marker: safe to finalize cleanup.
                check(File(destination, READY).isFile && File(destination, OWNED).isFile) {
                    "Ambiguous SMAPI backup; refusing to replace or delete existing data"
                }
                check(previous.deleteRecursively()) { "Could not finalize SMAPI backup cleanup" }
            }
        }
        if (pending.exists()) {
            require(pending.isDirectory && File(pending, OWNED).isFile) {
                "Unexpected SMAPI staging directory; preserving it"
            }
            check(pending.deleteRecursively()) { "Could not clean interrupted SMAPI staging" }
        }
        // The marker remains on a promoted directory until backup cleanup completes.
        if (!previous.exists() && destination.isDirectory && File(destination, READY).isFile &&
            File(destination, OWNED).isFile) {
            File(destination, READY).delete()
            File(destination, OWNED).delete()
        }
    }

    fun install(
        archive: File,
        destination: File,
        checkActive: () -> Unit = {},
        onFile: (String, Int) -> Unit = { _, _ -> }
    ): Int {
        require(archive.isFile && archive.length() in 1..VerifiedReleaseAsset.MAX_SMAPI_BYTES) {
            "Invalid SMAPI archive size"
        }
        check(destination.parentFile != null) { "SMAPI destination has no parent" }
        check(destination.parentFile!!.isDirectory) { "SMAPI installation parent is unavailable" }
        recover(destination)
        require(!destination.exists() || destination.isDirectory) { "SMAPI destination is not a directory" }
        val pending = stage(destination)
        val previous = backup(destination)
        check(!pending.exists() && !previous.exists()) { "SMAPI transaction paths are occupied" }
        check(pending.mkdir()) { "Cannot create SMAPI staging directory" }
        File(pending, OWNED).writeText("1")
        var oldMoved = false
        var promoted = false
        try {
            val budget = ZipBudget(MAX_ENTRIES, MAX_SINGLE_BYTES, MAX_TOTAL_BYTES)
            val seen = mutableSetOf<String>()
            var count = 0
            ZipInputStream(archive.inputStream().buffered()).use { zip ->
                var entry = zip.nextEntry
                while (entry != null) {
                    checkActive()
                    budget.nextEntry()
                    val name = entry.name
                    require(name.isNotEmpty() && !name.startsWith('/') && '\\' !in name && '\u0000' !in name) {
                        "Unsafe SMAPI entry path"
                    }
                    val segments = name.trimEnd('/').split('/')
                    require(segments.all { it.isNotEmpty() && it != "." && it != ".." } &&
                        segments.first() !in setOf(OWNED, READY)) { "Unsafe SMAPI entry path" }
                    val collisionKey = name.trimEnd('/').lowercase(Locale.ROOT)
                    require(seen.add(collisionKey)) { "Duplicate SMAPI entry" }
                    val item = File(pending, name)
                    require(item.canonicalPath.startsWith(pending.canonicalPath + File.separator)) {
                        "SMAPI entry leaves installation directory"
                    }
                    if (entry.isDirectory) {
                        check(item.mkdirs() || item.isDirectory) { "Cannot create SMAPI directory" }
                    } else {
                        check(item.parentFile!!.mkdirs() || item.parentFile!!.isDirectory) {
                            "Cannot create SMAPI parent directory"
                        }
                        val guardedInput = object : FilterInputStream(zip) {
                            override fun read(b: ByteArray, off: Int, len: Int): Int {
                                checkActive()
                                return super.read(b, off, len)
                            }
                        }
                        item.outputStream().buffered().use { out -> budget.copyEntry(guardedInput, out) }
                        count++
                        onFile(name, count)
                    }
                    zip.closeEntry()
                    entry = zip.nextEntry
                }
            }
            check(count > 0) { "Empty SMAPI archive" }
            File(pending, READY).writeText("1")
            checkActive()
            if (destination.exists()) {
                check(destination.renameTo(previous)) { "Cannot preserve existing SMAPI installation" }
                oldMoved = true
            }
            check(pending.renameTo(destination)) { "Cannot activate staged SMAPI installation" }
            promoted = true
            // Crash here is recoverable: READY remains inside the promoted destination.
            if (oldMoved) check(previous.deleteRecursively()) { "Cannot finalize SMAPI backup" }
            check(File(destination, READY).delete()) { "Cannot clear SMAPI transaction marker" }
            check(File(destination, OWNED).delete()) { "Cannot clear SMAPI transaction marker" }
            return count
        } catch (failure: Exception) {
            if (oldMoved && !promoted && !destination.exists()) {
                if (!previous.renameTo(destination)) {
                    throw IllegalStateException("SMAPI rollback failed; preserved backup at ${previous.path}", failure)
                }
            }
            throw failure
        } finally {
            if (pending.exists() && File(pending, OWNED).isFile) pending.deleteRecursively()
        }
    }
}
