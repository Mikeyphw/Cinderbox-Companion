package com.sdvsync.qualification

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.sdvsync.R
import java.io.File
import java.io.FileOutputStream
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Debug-variant-only Android foreground worker. Never reads network, game or Steam data. */
class M20SyntheticWorkerService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var job: Job? = null
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() {
        super.onCreate()
        val channel = NotificationChannel("m20_synthetic", "M20 test-only worker", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        val notification: Notification = NotificationCompat.Builder(this, "m20_synthetic")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("M20 synthetic transfer test")
            .setContentText("Disposable local bytes only")
            .setOngoing(true).build()
        startForeground(23920, notification)
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Only exact app-private, previously owned test fixtures are accepted.
        val caseId = intent?.getStringExtra("case_id") ?: return START_NOT_STICKY
        val nonce = intent.getStringExtra("nonce") ?: return START_NOT_STICKY
        val file = try { File(M20WorkRoot.ownedWork(this, caseId, nonce), "synthetic-stream.bin") }
            catch (_: Exception) { stopSelf(startId); return START_NOT_STICKY }
        // A repeated start MUST NOT cancel/restart an existing transfer.
        if (job?.isActive == true) return START_NOT_STICKY
        job = scope.launch {
            try {
                repeat(96) { i ->
                    FileOutputStream(file, true).use { stream ->
                        stream.write(ByteArray(512) { ((i + it) and 0xff).toByte() })
                        stream.fd.sync()
                    }
                    delay(200)
                }
            } finally {
                stopSelf(startId)
            }
        }
        return START_NOT_STICKY
    }
    override fun onDestroy() { job?.cancel(); scope.cancel(); super.onDestroy() }
    companion object {
        fun start(context: Context, caseId: String, nonce: String) {
            context.startForegroundService(Intent(context, M20SyntheticWorkerService::class.java).apply {
                putExtra("case_id", caseId); putExtra("nonce", nonce)
            })
        }
        fun stop(context: Context) { context.stopService(Intent(context, M20SyntheticWorkerService::class.java)) }
    }
}

/** Production-debug side verifies ownership without relying on androidTest code. */
internal object M20WorkRoot {
    fun ownedWork(context: Context, caseId: String, nonce: String): File {
        require(Regex("[a-h][0-9]{2}[A-Za-z0-9]+").matches(caseId))
        require(Regex("[0-9a-f]{32}").matches(nonce))
        val sha = java.security.MessageDigest.getInstance("SHA-256")
            .digest("m20-v1:$nonce:$caseId".toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }.take(24)
        val files = context.filesDir.canonicalFile
        val dir = File(File(files, "m20-qualification-fixtures"), "m20-owned-$sha")
        val marker = File(dir, ".m20-owned-v1")
        check(marker.isFile && !java.nio.file.Files.isSymbolicLink(marker.toPath()) &&
            marker.readText() == "m20-v1:$caseId:$sha:$nonce")
        val work = File(dir, "work")
        check(work.isDirectory && work.canonicalFile.parentFile == dir.canonicalFile &&
            !java.nio.file.Files.isSymbolicLink(work.toPath()))
        return work
    }
}
