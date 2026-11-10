package com.sdvsync.fileaccess

import android.content.ComponentName
import android.content.ServiceConnection
import android.content.pm.PackageManager
import android.os.IBinder
import com.sdvsync.logging.AppLogger
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import rikka.shizuku.Shizuku

/**
 * File access using the Shizuku framework.
 * Runs a UserService with shell (UID 2000) or root (UID 0) privileges.
 * Can access /storage/emulated/0/Android/data/ without root.
 */
class ShizukuFileAccess : FileAccessStrategy {

    override val name = "Shizuku"

    companion object {
        private const val TAG = "ShizukuFileAccess"
        private const val CHUNK_SIZE = 51200 // 50KB - safe for Binder IPC

        @Volatile
        private var fileService: IFileService? = null
        @Volatile private var gameServiceDisconnected = false

        private val serviceConnection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
                if (binder != null && binder.pingBinder()) {
                    fileService = IFileService.Stub.asInterface(binder)
                    gameServiceDisconnected = false
                    AppLogger.d(TAG, "FileService connected")
                }
            }

            override fun onServiceDisconnected(name: ComponentName?) {
                fileService = null
                gameServiceDisconnected = true
                AppLogger.d(TAG, "FileService disconnected")
            }
        }

        private val userServiceArgs by lazy {
            Shizuku.UserServiceArgs(
                ComponentName(
                    "com.sdvsync",
                    FileService::class.java.name
                )
            )
                .processNameSuffix("file_service")
                .version(2)
        }

        fun isAvailable(): Boolean = try {
            Shizuku.pingBinder() &&
                Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        } catch (e: Exception) {
            false
        }

        fun isInstalled(packageManager: PackageManager): Boolean = try {
            @Suppress("DEPRECATION")
            packageManager.getPackageInfo("moe.shizuku.privileged.api", 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }

        fun isRunning(): Boolean = try {
            Shizuku.pingBinder()
        } catch (e: Exception) {
            false
        }

        fun isPermissionGranted(): Boolean = try {
            Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        } catch (e: Exception) {
            false
        }

        fun requestPermission(requestCode: Int = 1001) {
            try {
                Shizuku.requestPermission(requestCode)
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to request permission", e)
            }
        }

        fun bindService() {
            try {
                Shizuku.bindUserService(userServiceArgs, serviceConnection)
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to bind service", e)
            }
        }

        fun unbindService() {
            try {
                Shizuku.unbindUserService(userServiceArgs, serviceConnection, true)
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to unbind service", e)
            }
            fileService = null
        }

        fun isServiceBound(): Boolean = fileService != null

        /** Backwards-compatible nullable result for the existing Shizuku-first/root fallback. */
        suspend fun queryGameStatus(): Int? = queryGameStatusDiagnostic().processCode

        /**
         * Manually requested read-only diagnosis. At most two service binding attempts.
         * Never asks for permission itself, exposes exceptions or authorizes mod changes.
         */
        suspend fun queryGameStatusDiagnostic(): ShizukuGameDiagnostic {
            if (!runCatching { Shizuku.pingBinder() }.getOrDefault(false)) {
                return ShizukuGameDiagnostic.BINDER_NOT_READY
            }
            val permission = runCatching { Shizuku.checkSelfPermission() }
                .getOrElse { return ShizukuGameDiagnostic.PERMISSION_CHECK_FAILED }
            if (permission != PackageManager.PERMISSION_GRANTED) {
                return ShizukuGameDiagnostic.PERMISSION_DENIED
            }
            val existing = fileService
            if (existing != null && runCatching { existing.asBinder().pingBinder() }
                    .getOrDefault(false)) return readGameStatusFromService(existing)
            fileService = null

            var lastFailure = ShizukuGameDiagnostic.SERVICE_TIMEOUT
            repeat(2) { attempt ->
                // Shizuku dispatches service connection callbacks on the main looper.
                // Binding is asynchronous; repeating is bounded and does not unbind or kill
                // the service used by save operations elsewhere in Cinderbox.
                try {
                    Shizuku.bindUserService(userServiceArgs, serviceConnection)
                } catch (_: Exception) {
                    lastFailure = ShizukuGameDiagnostic.SERVICE_BIND_FAILED
                    if (attempt == 1) return lastFailure
                    delay(150L)
                    return@repeat
                }
                val connected = if (attempt == 0) {
                    withTimeoutOrNull(2500L) { awaitGameService() }
                } else {
                    withTimeoutOrNull(1500L) { awaitGameService() }
                }
                if (connected != null) return readGameStatusFromService(connected)
                lastFailure = when {
                    !runCatching { Shizuku.pingBinder() }.getOrDefault(false) ->
                        ShizukuGameDiagnostic.BINDER_NOT_READY
                    gameServiceDisconnected -> ShizukuGameDiagnostic.SERVICE_DISCONNECTED
                    else -> ShizukuGameDiagnostic.SERVICE_TIMEOUT
                }
                if (attempt == 1 || !ShizukuDiagnosticPolicy.shouldRetryConnection(lastFailure)) {
                    return lastFailure
                }
                delay(150L)
            }
            return lastFailure
        }

        private suspend fun awaitGameService(): IFileService? {
            while (true) {
                val current = fileService
                if (current != null && runCatching { current.asBinder().pingBinder() }
                        .getOrDefault(false)) return current
                if (!runCatching { Shizuku.pingBinder() }.getOrDefault(false)) return null
                delay(75L)
            }
        }

        private suspend fun readGameStatusFromService(service: IFileService): ShizukuGameDiagnostic {
            return try {
                val code = withContext(Dispatchers.IO) { service.queryGameProcessStatus() }
                ShizukuDiagnosticPolicy.fromProcessCode(code)
            } catch (_: Exception) {
                fileService = null
                ShizukuGameDiagnostic.REMOTE_CALL_FAILED
            }
        }
    }

    private fun requireService(): IFileService = fileService ?: throw IllegalStateException(
        "Shizuku FileService not bound. Call ShizukuFileAccess.bindService() first."
    )

    override suspend fun exists(file: File): Boolean = withContext(Dispatchers.IO) {
        requireService().fileExists(file.absolutePath)
    }

    override suspend fun listDirectories(dir: File): List<String>? = withContext(Dispatchers.IO) {
        try {
            val entries = requireService().listDirectory(dir.absolutePath)
            entries.filter { it.startsWith("D|") }
                .map { it.removePrefix("D|") }
                .ifEmpty { null }
        } catch (e: Exception) {
            AppLogger.e(TAG, "listDirectories failed: ${dir.absolutePath}", e)
            null
        }
    }

    override suspend fun listFiles(dir: File): List<String>? = withContext(Dispatchers.IO) {
        try {
            val entries = requireService().listDirectory(dir.absolutePath)
            entries.filter { it.startsWith("F|") }
                .map { it.removePrefix("F|") }
                .ifEmpty { null }
        } catch (e: Exception) {
            AppLogger.e(TAG, "listFiles failed: ${dir.absolutePath}", e)
            null
        }
    }

    override suspend fun readFile(file: File): ByteArray? = withContext(Dispatchers.IO) {
        try {
            val service = requireService()
            val size = service.getFileSize(file.absolutePath)
            if (size <= 0) return@withContext null

            val result = ByteArray(size.toInt())
            var offset = 0L
            while (offset < size) {
                val chunkLen = minOf(CHUNK_SIZE.toLong(), size - offset).toInt()
                val chunk = service.readFileChunk(file.absolutePath, offset, chunkLen)
                chunk.copyInto(result, offset.toInt())
                offset += chunk.size
            }
            result
        } catch (e: Exception) {
            AppLogger.e(TAG, "readFile failed: ${file.absolutePath}", e)
            null
        }
    }

    override suspend fun writeFile(file: File, data: ByteArray): Boolean = withContext(Dispatchers.IO) {
        try {
            val service = requireService()
            val path = file.absolutePath

            if (data.size <= CHUNK_SIZE) {
                service.writeFileChunk(path, data, 0L)
            } else {
                var offset = 0L
                while (offset < data.size) {
                    val end = minOf(offset + CHUNK_SIZE, data.size.toLong())
                    val chunk = data.copyOfRange(offset.toInt(), end.toInt())
                    service.writeFileChunk(path, chunk, offset)
                    offset += chunk.size
                }
            }
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "writeFile failed: ${file.absolutePath}", e)
            false
        }
    }

    override suspend fun deleteFile(file: File): Boolean = withContext(Dispatchers.IO) {
        try {
            requireService().deleteFile(file.absolutePath)
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "deleteFile failed: ${file.absolutePath}", e)
            false
        }
    }

    override suspend fun renameFile(from: File, to: File): Boolean = withContext(Dispatchers.IO) {
        try {
            requireService().renameFile(from.absolutePath, to.absolutePath)
        } catch (e: Exception) {
            AppLogger.e(TAG, "renameFile failed: ${from.absolutePath}", e)
            false
        }
    }

    override suspend fun mkdirs(dir: File): Boolean = withContext(Dispatchers.IO) {
        try {
            requireService().createDirectory(dir.absolutePath)
            true
        } catch (e: Exception) {
            AppLogger.e(TAG, "mkdirs failed: ${dir.absolutePath}", e)
            false
        }
    }
}
