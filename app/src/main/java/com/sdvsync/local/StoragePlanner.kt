package com.sdvsync.local

import java.io.File
import java.nio.file.Files

/** Conservative same-filesystem free-space estimate. No Steam depot size is inferred. */
data class StorageBudget(
    val availableBytes: Long?,
    val payloadBytes: Long?,
    val reserveBytes: Long,
    val requiredBytes: Long?,
    val sufficient: Boolean?,
    val detail: String,
    val temporaryBytes: Long = 0L,
    val backupBytes: Long = 0L
)

object StoragePlanner {
    const val DEFAULT_RESERVE: Long = 256L * 1024 * 1024

    /** Optional *user-provided* estimate in GiB, never represented as a Steam-reported size. */
    fun parseGiB(input: String): Long? {
        if (input.isBlank()) return null
        val gib = input.toLongOrNull()
        require(gib != null && gib in 1..500) { "Estimated game size must be 1–500 GiB" }
        return Math.multiplyExact(gib, 1024L * 1024 * 1024)
    }

    fun plan(destination: File, payloadBytes: Long? = null,
             reserveBytes: Long = DEFAULT_RESERVE,
             temporaryBytes: Long = 0L, backupBytes: Long = 0L): StorageBudget {
        require(payloadBytes == null || payloadBytes >= 0) { "Negative payload size" }
        require(reserveBytes >= 0 && temporaryBytes >= 0 && backupBytes >= 0) {
            "Negative storage budget component"
        }
        val writable = StoragePreflight.check(destination)
        if (!writable.writable) return StorageBudget(null, payloadBytes, reserveBytes, null,
            false, writable.details)
        var existing = destination.absoluteFile
        while (!existing.exists()) existing = existing.parentFile
            ?: return StorageBudget(null, payloadBytes, reserveBytes, null, false, "Storage parent unavailable")
        var node: File? = existing
        while (node != null) {
            if (Files.isSymbolicLink(node.toPath())) return StorageBudget(null, payloadBytes,
                reserveBytes, null, false, "Storage path contains a symlink")
            node = node.parentFile
        }
        val usable = existing.usableSpace.takeIf { it > 0L }
            ?: return StorageBudget(null, payloadBytes, reserveBytes, null, null,
                "Available capacity is unknown; do not assume this storage is sufficient")
        val needed = try {
            Math.addExact(Math.addExact(payloadBytes ?: 0L, reserveBytes),
                Math.addExact(temporaryBytes, backupBytes))
        }
        catch (_: ArithmeticException) { return StorageBudget(usable, payloadBytes, reserveBytes,
            null, false, "Required capacity exceeds supported range") }
        return if (payloadBytes == null) {
            StorageBudget(usable, null, reserveBytes, null, null,
                "Game download size unknown. Free space shown is informational; allow extra extraction/verification space")
        } else StorageBudget(usable, payloadBytes, reserveBytes, needed, usable >= needed,
            if (usable >= needed) "Estimate fits with temporary and backup allowances (not a Steam size guarantee)"
            else "Not enough space for estimated data, temporary work, backups, and reserve",
            temporaryBytes, backupBytes)
    }

    /** Temporary allowance is a *user-estimate heuristic*, not a depot or ZIP manifest. */
    fun downloadPlan(destination: File, estimatedBytes: Long?): StorageBudget =
        plan(destination, estimatedBytes, temporaryBytes = estimatedBytes?.div(4) ?: 0L)

    /** All source files are counted, even if targets may exist (conservative estimate). */
    fun copyPlan(destination: File, sources: Collection<File>): StorageBudget {
        require(sources.isNotEmpty()) { "No source files to copy" }
        var total = 0L
        for (source in sources) {
            require(source.isFile && !Files.isSymbolicLink(source.toPath())) { "Unsafe game copy source" }
            var ancestor: File? = source.absoluteFile.parentFile
            while (ancestor != null) {
                require(!Files.isSymbolicLink(ancestor.toPath())) { "Game copy source contains symlink" }
                ancestor = ancestor.parentFile
            }
            total = Math.addExact(total, source.length())
        }
        return plan(destination, total)
    }
}
