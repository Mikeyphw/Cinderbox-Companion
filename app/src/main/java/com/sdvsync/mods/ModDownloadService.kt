package com.sdvsync.mods

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.sdvsync.MainActivity
import com.sdvsync.R
import com.sdvsync.logging.AppLogger
import com.sdvsync.local.StoragePreflight
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.mods.models.InstallResult
import com.sdvsync.mods.models.ModDownloadProgress
import com.sdvsync.mods.models.ModDownloadState
import java.io.File
import java.io.IOException
import java.util.ArrayDeque
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.update
import okhttp3.Call
import okhttp3.OkHttpClient
import okhttp3.Request
import org.koin.android.ext.android.inject

/** Serial bounded transfer worker. Never persists temporary Nexus download URLs. */
class ModDownloadService : Service() {
    companion object {
        private const val TAG = "ModDownloadService"
        private const val CHANNEL = "mod_download"
        private const val RESULTS_CHANNEL = "mod_download_results"
        private const val FOREGROUND_ID = 3
        private const val MAX_ARCHIVE_BYTES = 1_073_741_824L
        // Each completion gets its own notification and independent job deep link.
        private fun resultIdFor(jobId: String) = 100 + ((jobId.hashCode() and Int.MAX_VALUE) % 1_000_000_000)
        private const val EXTRA_URL = "url"
        private const val EXTRA_MOD_NAME = "mod_name"
        private const val EXTRA_MOD_ID = "mod_id"
        private const val EXTRA_SOURCE = "source"
        private const val EXTRA_FILE_ID = "file_id"
        private const val EXTRA_JOB_ID = "job_id"
        private const val ACTION_PAUSE_JOB = "com.sdvsync.mods.PAUSE_JOB"
        private const val ACTION_RESUME_JOB = "com.sdvsync.mods.RESUME_JOB"
        private const val ACTION_CANCEL_JOB = "com.sdvsync.mods.CANCEL_JOB"
        private const val ACTION_MOVE_UP = "com.sdvsync.mods.MOVE_UP"
        private const val ACTION_MOVE_DOWN = "com.sdvsync.mods.MOVE_DOWN"

        private fun control(context: Context, actionId: String, jobId: String) {
            // Explicit in-app action. No bearer URLs or credentials in control intents.
            val intent = Intent(context, ModDownloadService::class.java).apply {
                action = actionId
                putExtra(EXTRA_JOB_ID, jobId)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent)
            else context.startService(intent)
        }
        fun pause(context: Context, id: String) = control(context, ACTION_PAUSE_JOB, id)
        fun resume(context: Context, id: String) = control(context, ACTION_RESUME_JOB, id)
        fun cancelOne(context: Context, id: String) = control(context, ACTION_CANCEL_JOB, id)
        fun move(context: Context, id: String, delta: Int) = control(context,
            if (delta == -1) ACTION_MOVE_UP else ACTION_MOVE_DOWN, id)

        fun start(context: Context, url: String, modName: String, modId: String,
                  source: String, fileId: String, jobId: String) {
            val intent = Intent(context, ModDownloadService::class.java).apply {
                putExtra(EXTRA_URL, url)
                putExtra(EXTRA_MOD_NAME, modName)
                putExtra(EXTRA_MOD_ID, modId)
                putExtra(EXTRA_SOURCE, source)
                putExtra(EXTRA_FILE_ID, fileId)
                putExtra(EXTRA_JOB_ID, jobId)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent)
            else context.startService(intent)
        }

        fun stop(context: Context) { context.stopService(Intent(context, ModDownloadService::class.java)) }
    }

    private data class Work(val id: String, val url: String, val name: String,
        val modId: String, val source: String, val fileId: String)
    private val httpClient: OkHttpClient by inject()
    private val fileManager: ModFileManager by inject()
    private val dataStore: ModDataStore by inject()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val workLock = Any()
    private val queue = ArrayDeque<Work>()
    // These authorizations are process-local only; restart requires exact-file re-authorization.
    private val paused = mutableMapOf<String, Work>()
    private var activeCall: Call? = null
    private var activePhase = "IDLE"
    private var pauseRequested: String? = null
    private var cancelRequested: String? = null
    private var worker: Job? = null
    private var lastStartId = 0
    private var activeId: String? = null
    private val journal by lazy { ModDownloadJournal(this) }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startForeground(FOREGROUND_ID, progressNotification("Preparing mod downloads", null))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        synchronized(workLock) { lastStartId = startId }
        if (intent?.action in setOf(ACTION_PAUSE_JOB, ACTION_RESUME_JOB,
                ACTION_CANCEL_JOB, ACTION_MOVE_UP, ACTION_MOVE_DOWN)) {
            val id = intent?.getStringExtra(EXTRA_JOB_ID).orEmpty()
            if (id.isNotBlank()) handleControl(intent?.action.orEmpty(), id)
            synchronized(workLock) {
                if (queue.isEmpty() && activeId == null && paused.isEmpty()) stopSelfResult(startId)
            }
            return START_NOT_STICKY
        }
        val url = intent?.getStringExtra(EXTRA_URL) ?: return START_NOT_STICKY
        val id = intent?.getStringExtra(EXTRA_JOB_ID) ?: return START_NOT_STICKY
        val next = Work(id, url, intent.getStringExtra(EXTRA_MOD_NAME) ?: "Unknown mod",
            intent.getStringExtra(EXTRA_MOD_ID) ?: "", intent.getStringExtra(EXTRA_SOURCE) ?: "",
            intent.getStringExtra(EXTRA_FILE_ID) ?: "")
        synchronized(workLock) {
            lastStartId = startId
            if (queue.size + paused.size + (if (activeId != null) 1 else 0) >= 24) {
                journal.update(id, "FAILED", detail = "Queue is full; try again later")
                postResultNotification(id, "Download queue full", "Try again later")
                return START_NOT_STICKY
            }
            queue.addLast(next)
            if (worker?.isActive != true) worker = scope.launch { drain() }
        }
        return START_NOT_STICKY
    }

    private suspend fun drain() {
        while (true) {
            val next = synchronized(workLock) {
                if (queue.isEmpty()) { worker = null; null }
                else queue.removeFirst().also {
                    activeId = it.id
                    activePhase = "DOWNLOADING"
                }
            } ?: break
            runTransfer(next)
            synchronized(workLock) {
                activeCall = null
                activeId = null
                activePhase = "IDLE"
                pauseRequested = null
                cancelRequested = null
            }
        }
        // A new start command can create a new worker before this point.
        synchronized(workLock) {
            if (worker == null && queue.isEmpty() && paused.isEmpty()) stopSelfResult(lastStartId)
        }
    }

    private fun handleControl(action: String, id: String) {
        synchronized(workLock) {
            val waiting = queue.toMutableList()
            val index = waiting.indexOfFirst { it.id == id }
            val activeTransfer = activeId == id && activePhase == "DOWNLOADING"
            when (action) {
                ACTION_PAUSE_JOB -> when {
                    index >= 0 -> {
                        val work = waiting.removeAt(index)
                        queue.clear(); waiting.forEach(queue::addLast)
                        paused[id] = work
                        journal.update(id, "PAUSED", received = 0L, total = 0L,
                            detail = "Paused. Resume restarts from byte zero")
                    }
                    activeTransfer -> {
                        pauseRequested = id
                        activeCall?.cancel()
                    }
                }
                ACTION_CANCEL_JOB -> when {
                    index >= 0 -> {
                        waiting.removeAt(index)
                        queue.clear(); waiting.forEach(queue::addLast)
                        journal.cancelIfActive(id, "Cancelled individually")
                    }
                    paused.remove(id) != null -> journal.update(id, "CANCELLED",
                        detail = "Paused transfer cancelled")
                    activeTransfer -> {
                        cancelRequested = id
                        pauseRequested = null // Explicit cancel takes precedence over an earlier pause.
                        activeCall?.cancel()
                    }
                }
                ACTION_RESUME_JOB -> {
                    val work = paused[id]
                    if (work != null && journal.resumePaused(id)) {
                        paused.remove(id)
                        queue.addLast(work)
                        if (worker?.isActive != true) worker = scope.launch { drain() }
                    } else if (work == null && journal.list().any {
                        it.id == id && it.status == "PAUSED"
                    }) {
                        journal.update(id, "INTERRUPTED", received = 0L, total = 0L,
                            detail = "Session expired. Reopen the exact Nexus file to retry")
                    }
                }
                ACTION_MOVE_UP, ACTION_MOVE_DOWN -> {
                    val delta = if (action == ACTION_MOVE_UP) -1 else 1
                    val target = index + delta
                    if (index >= 0 && target in waiting.indices && journal.moveQueued(id, delta)) {
                        val moved = waiting.removeAt(index)
                        waiting.add(target, moved)
                        queue.clear(); waiting.forEach(queue::addLast)
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        synchronized(workLock) { activeCall?.cancel() }
        worker?.cancel()
        synchronized(workLock) {
            for ((id, _) in paused) journal.update(id, "INTERRUPTED",
                received = 0L, total = 0L, detail = "Session ended; fresh Nexus authorization needed")
            paused.clear()
            for (job in queue) journal.cancelIfActive(job.id, "Download stopped")
            queue.clear()
        }
        activeId?.let { journal.markJobInterrupted(it) }
        scope.cancel()
        super.onDestroy()
    }

    private suspend fun runTransfer(item: Work) {
        val tmp = File(cacheDir, "mod_download_${item.id}.zip")
        var downloaded = false
        var retainedForReview = false
        var phase = "storage"
        try {
            StoragePreflight.requireWritable(File(CinderboxPaths.MODS_DIR))
            StoragePreflight.requireWritable(cacheDir)
            phase = "transfer"
            journal.update(item.id, "DOWNLOADING", detail = "Downloading archive")
            ModDownloadManager._progress.value = ModDownloadProgress(
                state = ModDownloadState.DOWNLOADING, modName = item.name)
            updateProgressNotification("Downloading ${item.name.take(60)}")
            fetch(item, tmp)
            // The control and phase transition share a lock: no pause/cancel may
            // be accepted once validation or installation has begun.
            synchronized(workLock) {
                if (pauseRequested == item.id || cancelRequested == item.id) {
                    throw IOException("User stopped transfer")
                }
                activePhase = "VALIDATING"
            }
            downloaded = true
            phase = "validation"
            journal.update(item.id, "VALIDATING", detail = "Checking archive and target folders")
            updateProgressNotification("Validating mod archive")
            if (ModDownloadPreferences.requiresApproval(this)) {
                ModReviewQueue(filesDir).enqueue(tmp, item.name, item.source, item.modId,
                    item.fileId, item.id)
                retainedForReview = true
                journal.update(item.id, "REVIEW_REQUIRED", detail = "Open Downloads to inspect and approve")
                ModDownloadManager._progress.value = ModDownloadProgress(
                    state = ModDownloadState.REVIEW_REQUIRED, modName = item.name)
                postResultNotification(item.id, "Mod ready for review", "Open Downloads to approve or discard")
            } else {
                // The exact same ZIP, destination fingerprint, archive budget and journaled
                // atomic installer used by the manual review path remain mandatory.
                val preview = fileManager.previewFromZip(tmp)
                phase = "installation"
                synchronized(workLock) { activePhase = "INSTALLING" }
                journal.update(item.id, "INSTALLING", detail = "Validated; installing with rollback protection")
                ModDownloadManager._progress.value = ModDownloadProgress(
                    state = ModDownloadState.INSTALLING, modName = item.name)
                updateProgressNotification("Installing ${item.name.take(60)}")
                when (val result = fileManager.installFromZip(tmp, preview.approvalKey)) {
                    is InstallResult.Success -> {
                        // Metadata failure must not masquerade as installation failure after
                        // a successful atomic write to the real Mods directory.
                        try {
                            if (item.source != "local") {
                                for (mod in result.mods) {
                                    dataStore.setModMetadata(mod.manifest.uniqueID,
                                        ModMetadata(installedFrom = "${item.source}:${item.modId}",
                                            installedAt = System.currentTimeMillis()))
                                }
                            }
                        } catch (metadataError: Exception) {
                            AppLogger.e(TAG, "Install succeeded, metadata update failed", metadataError)
                        }
                        journal.update(item.id, "INSTALLED", detail = "Installed successfully; snapshots retained")
                        ModDownloadManager._progress.value = ModDownloadProgress(
                            state = ModDownloadState.COMPLETED, modName = item.name)
                        postResultNotification(item.id, "Mod installed", "Open Downloads for details")
                    }
                    is InstallResult.Error -> error("Installation blocked by safety checks")
                }
            }
        } catch (cancelled: CancellationException) {
            val advancedPhase = synchronized(workLock) {
                activePhase == "VALIDATING" || activePhase == "INSTALLING"
            }
            journal.update(item.id, if (advancedPhase) "VERIFY_REQUIRED" else "INTERRUPTED",
                detail = if (advancedPhase) "Installation interrupted; verify Mods before retry"
                else "Transfer interrupted; reopen the exact Nexus file")
            ModDownloadManager._progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                modName = item.name, errorMessage = "Download cancelled")
            throw cancelled
        } catch (e: Exception) {
            val controlled = synchronized(workLock) {
                when {
                    cancelRequested == item.id -> "CANCELLED"
                    pauseRequested == item.id -> "PAUSED"
                    else -> null
                }
            }
            if (controlled != null && !downloaded) {
                if (controlled == "PAUSED") {
                    synchronized(workLock) { paused[item.id] = item }
                    journal.update(item.id, "PAUSED", received = 0L, total = 0L,
                        detail = "Paused. Resume restarts from byte zero")
                    updateProgressNotification("Paused ${item.name.take(60)}")
                } else {
                    journal.update(item.id, "CANCELLED", received = 0L, total = 0L,
                        detail = "Transfer cancelled individually")
                }
                ModDownloadManager._progress.value = ModDownloadProgress()
                return
            }
            // A fully downloaded but unsafe/rejected archive remains private for explicit
            // inspection. Incomplete network downloads are discarded, never staged.
            if (downloaded && !retainedForReview) {
                retainedForReview = runCatching {
                    ModReviewQueue(filesDir).enqueue(tmp, item.name, item.source, item.modId,
                        item.fileId, item.id)
                    true
                }.getOrDefault(false)
            }
            AppLogger.e(TAG, "Mod download or installation failed (${e.javaClass.simpleName})")
            val safeFailure = when (phase) {
                "storage" -> "Storage unavailable; check game folder permissions and free space"
                "transfer" -> "Network transfer failed; reopen the Nexus file to retry"
                "validation" -> "Archive could not be validated or staged; inspect before installation"
                "installation" -> "Installation blocked by safety checks; inspect the archive"
                else -> "Download failed; reopen the Nexus file to retry"
            }
            journal.update(item.id, if (retainedForReview) "BLOCKED" else "FAILED",
                detail = safeFailure)
            ModDownloadManager._progress.value = ModDownloadProgress(state = ModDownloadState.ERROR,
                modName = item.name,
                errorMessage = if (retainedForReview) "Review downloaded archive" else "Download failed")
            postResultNotification(item.id, "Mod needs attention", "Open Downloads for details")
        } finally {
            if (tmp.exists()) tmp.delete()
        }
    }

    private suspend fun fetch(item: Work, dest: File) = withContext(Dispatchers.IO) {
        // Do not log or persist item.url: it can contain time-limited Nexus credentials.
        val request = Request.Builder().url(item.url).get().build()
        val call = httpClient.newCall(request)
        synchronized(workLock) {
            activeCall = call
            if (pauseRequested == item.id || cancelRequested == item.id) call.cancel()
        }
        try { call.execute().use { response ->
            if (!response.isSuccessful) throw IOException("Provider HTTP error")
            val body = response.body ?: throw IOException("Empty response")
            val total = body.contentLength()
            if (total > MAX_ARCHIVE_BYTES) throw IOException("Archive exceeds download budget")
            var received = 0L
            var lastReported = 0L
            var lastReportedAt = 0L
            val buffer = ByteArray(64 * 1024)
            dest.outputStream().buffered().use { output ->
                body.byteStream().use { input ->
                    while (true) {
                        ensureActive()
                        val count = input.read(buffer)
                        if (count < 0) break
                        output.write(buffer, 0, count)
                        received += count
                        if (received > MAX_ARCHIVE_BYTES) throw IOException("Archive exceeds download budget")
                        ModDownloadManager._progress.update {
                            it.copy(downloadedBytes = received, totalBytes = total)
                        }
                        val now = android.os.SystemClock.elapsedRealtime()
                        if ((received - lastReported >= 262144 && now - lastReportedAt >= 400) ||
                            (total > 0 && received == total)) {
                            journal.update(item.id, "DOWNLOADING", received, total.coerceAtLeast(0L),
                                "Downloading archive")
                            updateProgressNotification("Downloading ${item.name.take(60)}",
                                if (total > 0) ((received * 100L) / total).toInt().coerceIn(0, 100)
                                else null)
                            lastReported = received
                            lastReportedAt = now
                        }
                    }
                }
            }
            if (received <= 0L || (total > 0 && received != total)) throw IOException("Incomplete archive")
            journal.update(item.id, "DOWNLOADING", received, total.coerceAtLeast(0L),
                "Download transferred; checking archive")
        } } finally {
            synchronized(workLock) { if (activeCall === call) activeCall = null }
        }
    }

    private fun contentIntent(jobId: String? = null): PendingIntent {
        val destination = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            putExtra("cinderbox_open_downloads", true)
            // Never attach the provider URL or an auth token to a notification intent.
            if (jobId != null) putExtra("cinderbox_download_job_id", jobId)
        }
        return PendingIntent.getActivity(this, jobId?.let(::resultIdFor) ?: 3, destination,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    private fun createNotificationChannels() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL,
            getString(R.string.mods_download_notification_channel), NotificationManager.IMPORTANCE_LOW))
        manager.createNotificationChannel(NotificationChannel(RESULTS_CHANNEL,
            "Mod download results", NotificationManager.IMPORTANCE_DEFAULT))
    }

    private fun progressNotification(text: String, percent: Int?): Notification =
        NotificationCompat.Builder(this, CHANNEL)
            .setContentTitle("Cinderbox downloads")
            .setContentText(text).setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentIntent(contentIntent()).setOngoing(true)
            .apply { if (percent == null) setProgress(0, 0, true)
                     else setProgress(100, percent, false) }
            .build()

    private fun updateProgressNotification(text: String, percent: Int? = null) {
        runCatching { getSystemService(NotificationManager::class.java)
            .notify(FOREGROUND_ID, progressNotification(text, percent)) }
    }

    private fun postResultNotification(jobId: String, title: String, description: String) {
        runCatching {
            getSystemService(NotificationManager::class.java).notify(resultIdFor(jobId),
                NotificationCompat.Builder(this, RESULTS_CHANNEL)
                    .setContentTitle(title).setContentText(description)
                    .setSmallIcon(android.R.drawable.stat_sys_download_done)
                    .setContentIntent(contentIntent(jobId)).setAutoCancel(true)
                    .setOngoing(false).build())
        }
    }
}
