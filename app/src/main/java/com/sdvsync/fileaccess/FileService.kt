package com.sdvsync.fileaccess

import android.os.RemoteException
import android.util.Log
import java.io.File
import java.io.RandomAccessFile
import kotlin.system.exitProcess

/**
 * Privileged Shizuku service. Every entry point enforces the save-directory boundary,
 * even when invoked by an unexpected Binder caller.
 */
class FileService : IFileService.Stub() {
    companion object {
        private const val TAG = "ShizukuFileService"
        private const val MAX_CHUNK = 51200
    }

    private fun checked(path: String): File = PrivilegedSavePaths.requireAllowed(File(path))
    private fun checkedChild(path: String): File = PrivilegedSavePaths.requireChild(File(path))

    override fun destroy() = exitProcess(0)

    override fun fileExists(path: String): Boolean = try {
        checked(path).exists()
    } catch (e: Exception) {
        Log.w(TAG, "fileExists denied", e)
        false
    }

    override fun listDirectory(path: String): Array<String> {
        val dir = checked(path)
        if (!dir.isDirectory) throw RemoteException("Not a directory")
        return (dir.listFiles() ?: return emptyArray())
            .filter { PrivilegedSavePaths.isWithin(dir, it) }
            .map { file -> (if (file.isDirectory) "D|" else "F|") + file.name }
            .toTypedArray()
    }

    override fun readFileChunk(path: String, offset: Long, length: Int): ByteArray {
        require(offset >= 0L && length in 1..MAX_CHUNK) { "Invalid read range" }
        val file = checkedChild(path)
        return try {
            RandomAccessFile(file, "r").use { raf ->
                if (offset >= raf.length()) return byteArrayOf()
                raf.seek(offset)
                val bytes = ByteArray(length)
                val read = raf.read(bytes)
                if (read < 0) byteArrayOf() else bytes.copyOf(read)
            }
        } catch (e: Exception) {
            Log.e(TAG, "readFileChunk failed", e)
            throw RemoteException("Unable to read save file")
        }
    }

    override fun getFileSize(path: String): Long {
        val file = checkedChild(path)
        return if (file.isFile) file.length() else -1
    }

    override fun writeFileChunk(path: String, data: ByteArray, offset: Long) {
        require(offset >= 0L && data.size <= MAX_CHUNK) { "Invalid write range" }
        val file = checkedChild(path)
        try {
            file.parentFile?.mkdirs()
            RandomAccessFile(file, "rw").use { raf ->
                if (offset == 0L) raf.setLength(0)
                raf.seek(offset)
                raf.write(data)
            }
        } catch (e: Exception) {
            Log.e(TAG, "writeFileChunk failed", e)
            throw RemoteException("Unable to write save file")
        }
    }

    override fun deleteFile(path: String) {
        val file = checkedChild(path)
        require(!file.isDirectory) { "Recursive deletion is not permitted" }
        if (file.exists() && !file.delete()) throw RemoteException("Unable to delete save file")
    }

    override fun createDirectory(path: String) {
        val dir = checked(path)
        if (!dir.isDirectory && !dir.mkdirs()) throw RemoteException("Unable to create directory")
    }

    override fun renameFile(fromPath: String, toPath: String): Boolean = try {
        checkedChild(fromPath).renameTo(checkedChild(toPath))
    } catch (e: Exception) {
        Log.e(TAG, "renameFile denied", e)
        false
    }
}
