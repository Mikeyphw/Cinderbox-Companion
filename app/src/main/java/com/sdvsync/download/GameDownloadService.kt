package com.sdvsync.download

import android.app.ActivityManager
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.local.M23CinderboxFirstPolicy
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
import com.sdvsync.local.InstallationScanner
import com.sdvsync.local.InstallHealth
import com.sdvsync.local.StoragePreflight
import com.sdvsync.local.StoragePlanner
import com.sdvsync.steam.SteamClientManager
import com.sdvsync.steam.SteamContentService
import `in`.dragonbra.javasteam.depotdownloader.DepotDownloader
import `in`.dragonbra.javasteam.depotdownloader.IDownloadListener
import `in`.dragonbra.javasteam.depotdownloader.data.AppItem
import `in`.dragonbra.javasteam.depotdownloader.data.DownloadItem
import java.io.File
import java.util.Collections
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.update
import org.koin.android.ext.android.inject

class GameDownloadService : Service() {

    companion object {
        private const val TAG = "GameDownloadService"
        private const val CHANNEL_ID = "game_download"
        private const val NOTIFICATION_ID = 2

        private const val EXTRA_BRANCH = "branch"
        private const val EXTRA_PASSWORD = "password"
        private const val EXTRA_INSTALL_DIR = "install_dir"
        private const val EXTRA_OS = "os"
        private const val EXTRA_VERIFY = "verify"
        private const val EXTRA_BUILD_ID = "steam_build_id"
        private const val EXTRA_ESTIMATE = "estimated_payload_bytes"

        fun start(
            context: Context,
            branch: String,
            password: String?,
            installDir: String,
            os: String,
            verify: Boolean = true,
            expectedBuildId: Long = 0L,
            estimatedPayloadBytes: Long? = null
        ) {
            val intent = Intent(context, GameDownloadService::class.java).apply {
                putExtra(EXTRA_BRANCH, branch)
                putExtra(EXTRA_PASSWORD, password)
                putExtra(EXTRA_INSTALL_DIR, installDir)
                putExtra(EXTRA_OS, os)
                putExtra(EXTRA_VERIFY, verify)
                putExtra(EXTRA_BUILD_ID, expectedBuildId)
                putExtra(EXTRA_ESTIMATE, estimatedPayloadBytes ?: 0L)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, GameDownloadService::class.java))
        }
    }

    private val clientManager: SteamClientManager by inject()
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var depotDownloader: DepotDownloader? = null
    private var downloadJob: Job? = null
    private val lastSpeedUpdateMs = AtomicLong(0L)
    private val lastSpeedBytes = AtomicLong(0L)

    // Track cumulative bytes per depot (callback values are cumulative, not deltas)
    private val depotBytes = ConcurrentHashMap<Int, Long>()
    private val failedItems = AtomicBoolean(false)

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification(getString(R.string.download_preparing)))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val branch = intent?.getStringExtra(EXTRA_BRANCH) ?: "public"
        val password = intent?.getStringExtra(EXTRA_PASSWORD)
        val installDir = intent?.getStringExtra(EXTRA_INSTALL_DIR) ?: return START_NOT_STICKY
        val os = intent.getStringExtra(EXTRA_OS) ?: "windows"
        val verify = intent.getBooleanExtra(EXTRA_VERIFY, true)
        val expectedBuildId = intent.getLongExtra(EXTRA_BUILD_ID, 0L)
        val estimatedPayloadBytes = intent.getLongExtra(EXTRA_ESTIMATE, 0L)

        downloadJob?.cancel()
        downloadJob = serviceScope.launch {
            runDownload(branch, password, installDir, os, verify,
                expectedBuildId, estimatedPayloadBytes)
        }

        return START_NOT_STICKY
    }

    override fun onDestroy() {
        AppLogger.d(TAG, "Service destroying, cancelling download")
        downloadJob?.cancel()
        try {
            depotDownloader?.close()
        } catch (_: Exception) {}
        depotDownloader = null
        serviceScope.cancel()

        val currentState = GameDownloadManager._progress.value.state
        if (currentState == DownloadState.DOWNLOADING ||
            currentState == DownloadState.PREPARING ||
            currentState == DownloadState.VERIFYING
        ) {
            GameDownloadManager._progress.value = DownloadProgress(
                state = DownloadState.CANCELLED,
                errorMessage = getString(R.string.download_cancelled)
            )
        }

        super.onDestroy()
    }

    private suspend fun runDownload(
        branch: String,
        password: String?,
        installDir: String,
        os: String,
        verify: Boolean,
        expectedBuildId: Long,
        estimatedPayloadBytes: Long
    ) {
        try {
            require(estimatedPayloadBytes > 0L) { "Download requires size estimate" }
            // This verifies PICS branch identity, NOT actual license/depot entitlement.
            require(verify && expectedBuildId > 0L) { "Unverified Steam build selection" }
            check(clientManager.isLoggedIn) { "Steam sign-in required" }
            val content = SteamContentService(clientManager)
            var sessionManifestFingerprint: String? = null
            var sessionDepotManifestIds: Map<Int, String>? = null
            suspend fun recheckBranch() {
                val selected = content.getAppBranches().branches.firstOrNull { it.name == branch }
                M24SteamSelectionPolicy.requireBound(clientManager.isLoggedIn, expectedBuildId, selected?.buildId)
                val fingerprint = selected?.manifestFingerprint
                    ?: error("PICS branch has no usable depot manifest IDs; no live transfer permitted")
                if (sessionManifestFingerprint != null) {
                    check(sessionManifestFingerprint == fingerprint) {
                        "Steam depot manifest identity changed during download; staged bytes preserved"
                    }
                }
                val ids = selected?.depotManifestIds ?: emptyMap()
                check(ids.isNotEmpty() && ids.size == selected?.depotCount) { "PICS depot manifest identities missing" }
                if (sessionDepotManifestIds != null) {
                    check(sessionDepotManifestIds == ids) { "PICS depot manifests changed" }
                }
                sessionDepotManifestIds = ids
                sessionManifestFingerprint = fingerprint
            }
            recheckBranch()
            val installRoot = File(installDir)
            // Defense in depth for restarted/explicit service intents, even if the
            // UI and GameDownloadManager path gates were bypassed.
            val scope = M23CinderboxFirstPolicy.assess(installRoot, File(CinderboxPaths.ROOT_DIR))
            check(scope.code != M23CinderboxFirstPolicy.Code.PROTECTED_CINDERBOX_TREE &&
                scope.code != M23CinderboxFirstPolicy.Code.UNSAFE_OR_NONABSOLUTE_DESTINATION &&
                scope.code != M23CinderboxFirstPolicy.Code.DESTINATION_UNREADABLE) {
                "Protected Cinderbox game tree or unsafe destination"
            }
            StoragePreflight.requireWritable(installRoot)
            check(StoragePlanner.downloadPlan(installRoot, estimatedPayloadBytes).sufficient == true) {
                "Insufficient or unknown available storage capacity"
            }
            // Only a checkpoint written by our manager authorizes touching partial files.
            // This also rejects intents manually dispatched to the service.
            GameDownloadRecovery(filesDir).requireMatching(installRoot, branch, os, verify)
            val recovery = GameDownloadRecovery(filesDir)
            recovery.requireSteamBuildId(expectedBuildId)
            val manifestFingerprint = checkNotNull(sessionManifestFingerprint)
            recovery.bindDepotManifestFingerprint(manifestFingerprint)
            recovery.requireDepotManifestFingerprint(manifestFingerprint)
            if (recovery.isPromotedStage(installRoot)) {
                // Crash occurred after atomic rename, before final ledger/journal
                // commit. Rehash the installed bytes without contacting downloader.
                verifyPromotedFiles(installRoot, checkNotNull(sessionDepotManifestIds))
                return
            }
            val stageRoot = recovery.requireActiveStage(installRoot)
            GameDownloadManager._progress.value = DownloadProgress(state = DownloadState.PREPARING)
            updateNotification(getString(R.string.download_preparing))

            val licenses = clientManager.licenses.value
            if (licenses.isEmpty()) {
                throw IllegalStateException(getString(R.string.download_error_no_licenses))
            }

            // VZipUtil allocates an 8MB ThreadLocal per decompress thread, plus ~2MB chunk data.
            val am = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val cpuCores = Runtime.getRuntime().availableProcessors()
            val heapBytes = am.largeMemoryClass.toLong() * 1024 * 1024
            val decompressCostBytes = 10L * 1024 * 1024

            // Tighter budget on low-heap devices where fragmentation limits contiguous allocation.
            val heapBudgetRatio = when {
                heapBytes >= 1024L * 1024 * 1024 -> 0.25 // 1GB+ heap: 25% budget
                heapBytes >= 768L * 1024 * 1024 -> 0.15 // 768MB heap: 15% budget
                else -> 0.08 // <=512MB heap: 8% budget (~41MB, ~4 threads max)
            }
            val maxDecompressByMem = (heapBytes * heapBudgetRatio / decompressCostBytes).toInt().coerceAtLeast(1)
            val maxDecompressByCpu = (cpuCores * 0.5).toInt().coerceIn(1, 4)
            val maxDecompress = minOf(maxDecompressByMem, maxDecompressByCpu)
            val maxDownloads = (cpuCores * 1.0).toInt().coerceIn(2, 8)
            val maxFileWrites = maxDecompress.coerceIn(1, 4)

            AppLogger.d(
                TAG,
                "Heap: ${am.largeMemoryClass}MB, CPU: $cpuCores cores → " +
                    "downloads=$maxDownloads, decompress=$maxDecompress, writes=$maxFileWrites"
            )

            val downloader = DepotDownloader(
                steamClient = clientManager.client,
                licenses = licenses,
                debug = false,
                maxDownloads = maxDownloads,
                maxDecompress = maxDecompress,
                maxFileWrites = maxFileWrites,
                parentJob = currentCoroutineContext()[Job]
            )
            depotDownloader = downloader

            lastSpeedUpdateMs.set(System.currentTimeMillis())
            lastSpeedBytes.set(0L)
            depotBytes.clear()
            failedItems.set(false)
            val completedFiles = Collections.synchronizedSet(mutableSetOf<String>())
            val completedDepots = Collections.synchronizedSet(mutableSetOf<Int>())

            downloader.addListener(object : IDownloadListener {
                override fun onDownloadStarted(item: DownloadItem) {
                    try {
                        AppLogger.d(TAG, "Download started for item")
                        // A second item can start after other depots already transferred data.
                        GameDownloadManager._progress.update { it.copy(state = DownloadState.DOWNLOADING) }
                        updateNotification(getString(R.string.download_downloading))
                    } catch (e: Exception) {
                        AppLogger.e(TAG, "Error in onDownloadStarted", e)
                    }
                }

                override fun onChunkCompleted(
                    depotId: Int,
                    depotPercentComplete: Float,
                    compressedBytes: Long,
                    uncompressedBytes: Long
                ) {
                    try {
                        // Callbacks are cumulative per depot and may arrive from parallel workers.
                        depotBytes.compute(depotId) { _, previous ->
                            maxOf(previous ?: 0L, uncompressedBytes.coerceAtLeast(0L))
                        }
                        val totalDownloaded = depotBytes.values.sum()
                        val depotPercent = if (depotPercentComplete.isFinite()) {
                            depotPercentComplete.coerceIn(0f, 1f)
                        } else 0f

                        val now = System.currentTimeMillis()
                        val lastUpdate = lastSpeedUpdateMs.get()
                        var speed = GameDownloadManager._progress.value.bytesPerSecond
                        if (now - lastUpdate >= 500) {
                            if (lastSpeedUpdateMs.compareAndSet(lastUpdate, now)) {
                                val prevBytes = lastSpeedBytes.getAndSet(totalDownloaded)
                                val elapsedMs = now - lastUpdate
                                val bytesDelta = totalDownloaded - prevBytes
                                speed = if (elapsedMs > 0) (bytesDelta.coerceAtLeast(0L) * 1000 / elapsedMs) else 0L
                            }
                        }

                        GameDownloadManager._progress.update { current ->
                            current.copy(
                                // Do not misrepresent one depot's progress as game-wide progress.
                                currentDepotId = depotId,
                                currentDepotPercent = depotPercent,
                                downloadedBytes = maxOf(current.downloadedBytes, totalDownloaded),
                                bytesPerSecond = speed
                            )
                        }
                    } catch (e: Exception) {
                        AppLogger.e(TAG, "Error in onChunkCompleted", e)
                    }
                }

                override fun onFileCompleted(depotId: Int, fileName: String, depotPercentComplete: Float) {
                    try {
                        completedFiles.add(fileName)
                        GameDownloadManager._progress.update { current ->
                            current.copy(
                                currentFile = fileName,
                                filesDownloaded = completedFiles.size,
                                currentDepotId = depotId,
                                currentDepotPercent = if (depotPercentComplete.isFinite()) {
                                    depotPercentComplete.coerceIn(0f, 1f)
                                } else current.currentDepotPercent
                            )
                        }
                        updateNotification(getString(R.string.download_downloading))
                    } catch (e: Exception) {
                        AppLogger.e(TAG, "Error in onFileCompleted", e)
                    }
                }

                override fun onDepotCompleted(depotId: Int, compressedBytes: Long, uncompressedBytes: Long) {
                    try {
                        AppLogger.d(TAG, "Depot $depotId completed: ${uncompressedBytes / 1024 / 1024} MB")
                        completedDepots.add(depotId)
                        depotBytes.compute(depotId) { _, previous ->
                            maxOf(previous ?: 0L, uncompressedBytes.coerceAtLeast(0L))
                        }
                        GameDownloadManager._progress.update { current ->
                            current.copy(downloadedBytes = maxOf(current.downloadedBytes, depotBytes.values.sum()))
                        }
                        // A completed depot does not reveal the total size of all depots.
                    } catch (e: Exception) {
                        AppLogger.e(TAG, "Error in onDepotCompleted", e)
                    }
                }

                override fun onDownloadCompleted(item: DownloadItem) {
                    AppLogger.d(TAG, "Download completed! (${completedFiles.size} files)")
                }

                override fun onDownloadFailed(item: DownloadItem, error: Throwable) {
                    failedItems.set(true)
                    try {
                        AppLogger.e(TAG, "Download failed", error)
                        GameDownloadManager._progress.value = DownloadProgress(
                            state = DownloadState.ERROR,
                            errorMessage = error.message ?: getString(R.string.download_error)
                        )
                        updateNotification(
                            getString(
                                R.string.download_notification_failed,
                                error.message ?: getString(R.string.download_error_unknown)
                            )
                        )
                    } catch (e: Exception) {
                        AppLogger.e(TAG, "Error in onDownloadFailed", e)
                    }
                }

                override fun onStatusUpdate(message: String) {
                    AppLogger.d(TAG, "Status: $message")
                }
            })

            val appItem = AppItem(
                appId = 413150,
                installToGameNameDirectory = false,
                installDirectory = stageRoot.absolutePath,
                branch = branch,
                branchPassword = password ?: "",
                downloadAllPlatforms = false,
                os = os,
                downloadAllArchs = false,
                osArch = "64",
                downloadAllLanguages = false,
                language = "english",
                lowViolence = false,
                depot = emptyList(),
                manifest = emptyList()
            )

            downloader.add(appItem)
            downloader.finishAdding()
            downloader.awaitCompletion()

            // A per-item callback can report failure without throwing awaitCompletion().
            check(!failedItems.get() && GameDownloadManager._progress.value.state != DownloadState.ERROR) {
                "Steam reported a failed depot or file download"
            }
            // An interrupted network session or branch update must not be recorded
            // as a successful download even if the SDK returned from awaitCompletion.
            recheckBranch()
            AppLogger.d(TAG, "Download pipeline finished; PICS build rechecked")

            // Every M24 live transfer requires a local SHA-256 ledger. This does
            // not attest an independent signed Steam depot manifest.
            verifyFiles(installDir, stageRoot, completedFiles, ::recheckBranch,
                checkNotNull(sessionManifestFingerprint), checkNotNull(sessionDepotManifestIds), completedDepots.toSet())
        } catch (e: CancellationException) {
            AppLogger.d(TAG, "Download cancelled")
            GameDownloadManager._progress.value = DownloadProgress(
                state = DownloadState.CANCELLED,
                errorMessage = getString(R.string.download_cancelled)
            )
        } catch (e: Exception) {
            AppLogger.e(TAG, "Download error", e)
            GameDownloadManager._progress.value = DownloadProgress(
                state = DownloadState.ERROR,
                errorMessage = e.message ?: getString(R.string.download_error_unknown)
            )
            updateNotification(
                getString(
                    R.string.download_notification_error,
                    e.message ?: getString(R.string.download_error_unknown)
                )
            )
        } finally {
            try {
                depotDownloader?.close()
            } catch (_: Exception) {}
            depotDownloader = null
            stopSelf()
        }
    }

    private suspend fun verifyPromotedFiles(destination: File, depotIds: Map<Int, String>,
        completedDepots: Set<Int>? = null) {
        M24DepotManifestCrosscheck.verify(destination, depotIds, completedDepots)
        // Interrupted after atomic promotion: no transfer or destructive replay.
        val report = GameFileIntegrity(filesDir).verifyAndRecord(destination)
        check(report.passed) { "Promoted files failed local SHA-256 verification" }
        GameDownloadRecovery(filesDir).completed()
        GameDownloadManager._progress.value = DownloadProgress(
            state = DownloadState.COMPLETED, overallPercent = 1f,
            verifiedFiles = report.files, totalFilesToVerify = report.files,
            verificationPassed = true,
            integrityScope = "PICS_BOUND_DEPOT_SHA1_UNSIGNED"
        )
    }

    /** Persist SHA-256 hashes and detect changed/unreadable game files.
     * This is local integrity checking; Steam authenticates chunks during transfer.
     */
    private suspend fun verifyFiles(installDir: String, stageRoot: File,
        completedFiles: Set<String>, recheckBranch: suspend () -> Unit,
        expectedManifestFingerprint: String, depotIds: Map<Int, String>,
        completedDepots: Set<Int>) {
        val root = stageRoot
        GameDownloadManager._progress.value = DownloadProgress(
            state = DownloadState.VERIFYING, totalFilesToVerify = completedFiles.size
        )
        updateNotification(getString(R.string.download_notification_verifying, 0))
        val activeJob = currentCoroutineContext()[Job]
        val report = GameFileIntegrity(filesDir).verifyAndRecord(root) { done, total, name ->
            activeJob?.ensureActive()
            val percent = if (total > 0) done.toFloat() / total else 0f
            GameDownloadManager._progress.update {
                it.copy(state = DownloadState.VERIFYING, verifiedFiles = done,
                    totalFilesToVerify = total, overallPercent = percent, currentFile = name)
            }
            if (done % maxOf(1, total / 20) == 0 || done == total) {
                updateNotification(getString(R.string.download_notification_verifying, (percent * 100).toInt()))
            }
        }
        if (!report.passed) {
            GameDownloadManager._progress.value = DownloadProgress(
                state = DownloadState.ERROR, verificationPassed = false,
                verifiedFiles = report.files, totalFilesToVerify = report.files,
                verificationErrors = report.errors,
                errorMessage = "Local game file integrity verification failed"
            )
            updateNotification("File verification failed. Retry to repair this download.")
            return
        }
        // Fail closed unless all PICS-bound depot manifests are cached and every
        // resulting staged file matches its manifest content hash. This does
        // not verify Valve's signature or independently prove entitlement.
        M24DepotManifestCrosscheck.verify(root, depotIds, completedDepots)
        // Final PICS check after hashing, before the only filesystem commit.
        recheckBranch()
        // Crash recovery must still own the same PICS manifest identity.
        GameDownloadRecovery(filesDir).requireDepotManifestFingerprint(expectedManifestFingerprint)
        // Atomic same-volume publish requires an ABSENT target. No copy fallback.
        GameDownloadRecovery(filesDir).promoteStaged(File(installDir))
        // The final ledger must refer to the published destination, not the stage.
        verifyPromotedFiles(File(installDir), depotIds, completedDepots)
        GameDownloadManager._progress.value = DownloadProgress(
            state = DownloadState.COMPLETED, overallPercent = 1f,
            verifiedFiles = report.files, totalFilesToVerify = report.files,
            verificationPassed = true,
            integrityScope = "PICS_BOUND_DEPOT_SHA1_UNSIGNED"
        )
        updateNotification(getString(R.string.download_complete))
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.download_notification_channel),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.download_notification_channel_desc)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        val progress = GameDownloadManager._progress.value
        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.download_notification_title))
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentIntent(pendingIntent)
            .setOngoing(true)

        when (progress.state) {
            DownloadState.DOWNLOADING, DownloadState.VERIFYING -> {
                builder.setProgress(100, (progress.overallPercent * 100).toInt(), false)
            }
            DownloadState.PREPARING -> {
                builder.setProgress(0, 0, true)
            }
            else -> {}
        }

        return builder.build()
    }

    private fun updateNotification(text: String) {
        try {
            val notification = buildNotification(text)
            val manager = getSystemService(NotificationManager::class.java)
            manager.notify(NOTIFICATION_ID, notification)
        } catch (_: Exception) {
            // Ignore notification update failures
        }
    }
}
