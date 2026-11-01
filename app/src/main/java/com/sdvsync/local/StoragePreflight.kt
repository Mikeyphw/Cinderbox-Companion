package com.sdvsync.local

import java.io.File
import java.nio.file.Files

/** Probe the *actual filesystem destination*, not a permission flag or unrelated SAF tree. */
data class StorageCheck(val writable: Boolean, val details: String)

object StoragePreflight {
    fun check(destination: File): StorageCheck {
        if (!destination.isAbsolute) return StorageCheck(false, "An absolute destination path is required")
        val safety = PlatformStoragePaths.inspect(destination)
        if (!safety.safe) return StorageCheck(false, safety.reason)
        if (destination.exists() && !destination.isDirectory)
            return StorageCheck(false, "Destination is not a directory")
        // Do not create folders just for checking; use the nearest existing parent.
        var existing = destination.absoluteFile
        while (!existing.exists()) {
            existing = existing.parentFile ?: return StorageCheck(false, "No accessible storage parent")
        }
        if (!existing.isDirectory || !existing.canWrite())
            return StorageCheck(false, "Storage folder is not writable or accessible")
        return try {
            val probe = Files.createTempFile(existing.toPath(), ".cinderbox-probe-", ".tmp")
            try { Files.write(probe, byteArrayOf(1)) } finally { Files.deleteIfExists(probe) }
            StorageCheck(true, if (destination.exists()) "Destination writable" else "Parent writable; new directory can be created")
        } catch (_: Exception) {
            StorageCheck(false, "Cannot safely create and remove a temporary test file")
        }
    }

    fun requireWritable(destination: File) {
        val result = check(destination)
        check(result.writable) { "Storage unavailable: ${result.details}" }
    }
}
