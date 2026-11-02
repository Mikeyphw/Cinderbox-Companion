package com.sdvsync.local

import java.io.File
import java.io.IOException
import java.nio.file.Files
import java.nio.file.InvalidPathException

/**
 * Distinguishes Android's OS-owned path aliases from links inside game/mod data.
 *
 * Only the exact platform-controlled *prefix components* below may be symbolic
 * links. Any link in the user-controlled suffix is rejected, even when it
 * resolves to a directory under the same storage tree. This code is read-only;
 * every mutating operation must revalidate at its own commit boundary.
 *
 * This is not a sandbox against a malicious root user or a mount swap between
 * inspection and opening a file. A SAF grant is not File API permission.
 */
object PlatformStoragePaths {
    private val androidOwnedAliases = setOf(
        "/sdcard", "/mnt/sdcard", "/storage", "/storage/emulated",
        "/storage/emulated/0", "/storage/self", "/storage/self/primary",
        "/mnt/user", "/mnt/user/0", "/mnt/user/0/primary",
        "/data/data", "/data/user", "/data/user/0",
        "/data/user_de", "/data/user_de/0"
    )

    data class Inspection(val safe: Boolean, val reason: String = "", val component: File? = null)

    /** Package-private test seam; production never accepts caller-supplied trust paths. */
    internal fun inspect(file: File, platformAliases: Set<String>): Inspection {
        if (!file.isAbsolute) return Inspection(false, "Absolute destination path required")
        if (file.path.split('/').any { it == "." || it == ".." })
            return Inspection(false, "Traversal component in destination path")
        var node: File? = file.absoluteFile
        try {
            while (node != null) {
                if (Files.isSymbolicLink(node.toPath())) {
                    // The path must be EXACTLY an OS-owned alias; no subtree
                    // inherits this privilege. Also refuse dangling OS aliases.
                    val shown = node.path.replace("\n", "\\n").replace("\r", "\\r")
                    if (node.path !in platformAliases)
                        return Inspection(false, "Untrusted symbolic link: $shown", node)
                    if (!Files.exists(node.toPath()))
                        return Inspection(false, "Unavailable Android storage alias: $shown", node)
                }
                node = node.parentFile
            }
            // Canonicalize after the component review; trusted symlink targets
            // have already been checked for availability above.
            file.canonicalFile
        } catch (_: InvalidPathException) {
            return Inspection(false, "Invalid destination path")
        } catch (_: IOException) {
            return Inspection(false, "Cannot resolve destination path")
        } catch (_: SecurityException) {
            return Inspection(false, "Destination path access denied")
        }
        return Inspection(true)
    }

    fun inspect(file: File): Inspection = inspect(file, androidOwnedAliases)

    fun requireSafe(file: File): File {
        val result = inspect(file)
        require(result.safe) { result.reason }
        return file.canonicalFile
    }
}
