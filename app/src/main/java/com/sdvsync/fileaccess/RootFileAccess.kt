package com.sdvsync.fileaccess

import com.sdvsync.logging.AppLogger
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Root access is never selected automatically. See FileAccessDetector for explicit opt-in.
 * Commands only accept canonical paths under the supported Stardew save directories.
 */
class RootFileAccess : FileAccessStrategy {
    override val name = "Root"

    private data class Result(val status: Int, val bytes: ByteArray) {
        val success: Boolean get() = status == 0
    }

    override suspend fun exists(file: File): Boolean = withContext(Dispatchers.IO) {
        val safe = PrivilegedSavePaths.requireAllowed(file)
        runRoot("test -e ${RootShell.quote(safe.absolutePath)}").success
    }

    override suspend fun listDirectories(dir: File): List<String>? = listEntries(dir, "d")

    override suspend fun listFiles(dir: File): List<String>? = listEntries(dir, "f")

    private suspend fun listEntries(dir: File, type: String): List<String>? = withContext(Dispatchers.IO) {
        val safe = PrivilegedSavePaths.requireAllowed(dir)
        val result = runRoot(
            "find ${RootShell.quote(safe.absolutePath)} -mindepth 1 -maxdepth 1 " +
                "-type $type -print0"
        )
        if (!result.success) return@withContext null
        result.bytes.toString(Charsets.UTF_8).split('\u0000')
            .filter(String::isNotEmpty)
            .map { File(it).name }
            .filter { name ->
                // Do not expose symlink entries or files that escape the save tree.
                PrivilegedSavePaths.isWithin(safe, File(safe, name))
            }
    }

    override suspend fun readFile(file: File): ByteArray? = withContext(Dispatchers.IO) {
        val safe = PrivilegedSavePaths.requireChild(file)
        val result = runRoot("cat ${RootShell.quote(safe.absolutePath)} 2>/dev/null")
        if (result.success) result.bytes else null
    }

    override suspend fun writeFile(file: File, data: ByteArray): Boolean = withContext(Dispatchers.IO) {
        val safe = PrivilegedSavePaths.requireChild(file)
        val staged = File.createTempFile("sdvsync_", ".tmp")
        try {
            staged.writeBytes(data)
            val result = runRoot(
                "cp ${RootShell.quote(staged.absolutePath)} ${RootShell.quote(safe.absolutePath)} " +
                    "&& chmod 660 ${RootShell.quote(safe.absolutePath)}"
            )
            result.success
        } catch (e: Exception) {
            AppLogger.e(TAG, "Root write failed", e)
            false
        } finally {
            staged.delete()
        }
    }

    override suspend fun deleteFile(file: File): Boolean = withContext(Dispatchers.IO) {
        val safe = PrivilegedSavePaths.requireChild(file)
        // Do not recursively delete a save directory through the root adapter.
        if (safe.isDirectory) return@withContext false
        runRoot("rm -f ${RootShell.quote(safe.absolutePath)}").success
    }

    override suspend fun renameFile(from: File, to: File): Boolean = withContext(Dispatchers.IO) {
        val source = PrivilegedSavePaths.requireChild(from)
        val dest = PrivilegedSavePaths.requireChild(to)
        runRoot("mv ${RootShell.quote(source.absolutePath)} ${RootShell.quote(dest.absolutePath)}").success
    }

    override suspend fun mkdirs(dir: File): Boolean = withContext(Dispatchers.IO) {
        val safe = PrivilegedSavePaths.requireAllowed(dir)
        runRoot(
            "mkdir -p ${RootShell.quote(safe.absolutePath)} " +
                "&& chmod 770 ${RootShell.quote(safe.absolutePath)}"
        ).success
    }

    private fun runRoot(command: String): Result = try {
        val process = ProcessBuilder("su", "-c", command).redirectErrorStream(true).start()
        val output = process.inputStream.use { it.readBytes() }
        Result(process.waitFor(), output)
    } catch (e: Exception) {
        AppLogger.e(TAG, "Root command failed", e)
        Result(-1, byteArrayOf())
    }

    companion object {
        private const val TAG = "RootFileAccess"

        /** Only invoke after a user has explicitly selected Root. */
        fun isAvailable(): Boolean = try {
            val process = ProcessBuilder("su", "-c", "id -u").redirectErrorStream(true).start()
            val output = process.inputStream.bufferedReader().use { it.readText() }
            process.waitFor() == 0 && output.trim() == "0"
        } catch (_: Exception) {
            false
        }
    }
}
