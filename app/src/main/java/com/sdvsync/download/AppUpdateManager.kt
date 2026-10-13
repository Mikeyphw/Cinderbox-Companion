package com.sdvsync.download

import android.content.Context
import com.sdvsync.BuildConfig
import com.sdvsync.logging.AppLogger
import java.io.File
import java.security.MessageDigest
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

class AppUpdateManager(
    private val context: Context,
    private val httpClient: OkHttpClient,
    private val releaseChecker: GitHubReleaseChecker
) {
    companion object {
        private const val TAG = "AppUpdateManager"
        private const val PREFS_NAME = "app_update"
        private const val KEY_UPDATE_CHECK_ENABLED = "update_check_enabled"
        private const val KEY_SKIPPED_VERSION = "skipped_version"
    }

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun isUpdateCheckEnabled(): Boolean = prefs.getBoolean(KEY_UPDATE_CHECK_ENABLED, true)

    fun setUpdateCheckEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_UPDATE_CHECK_ENABLED, enabled).apply()
    }

    fun getSkippedVersion(): String? = prefs.getString(KEY_SKIPPED_VERSION, null)

    fun setSkippedVersion(version: String?) {
        prefs.edit().apply {
            if (version == null) remove(KEY_SKIPPED_VERSION) else putString(KEY_SKIPPED_VERSION, version)
        }.apply()
    }

    fun shouldShowUpdate(latestVersion: String): Boolean {
        if (!isUpdateCheckEnabled()) return false
        if (!releaseChecker.isUpdateAvailable(BuildConfig.VERSION_NAME, latestVersion)) return false
        if (latestVersion == getSkippedVersion()) return false
        return true
    }

    fun canInstallPackages(): Boolean = context.packageManager.canRequestPackageInstalls()

    /** Download to an isolated temporary APK, verify it, then publish atomically. */
    @Suppress("DEPRECATION")
    suspend fun downloadUpdate(release: GitHubReleaseInfo, onProgress: (Float) -> Unit): File? =
        withContext(Dispatchers.IO) {
            val expected = try {
                TrustedUpdate.expectedSha256(
                    release.assetUrl, release.assetName, release.assetSize, release.assetDigest
                )
            } catch (e: Exception) {
                AppLogger.e(TAG, "Untrusted update release metadata", e)
                return@withContext null
            }
            val apk = File(context.cacheDir, "cinderbox_update_$expected.apk")
            val staging = File(context.cacheDir, "cinderbox_update_$expected.partial.apk")
            staging.delete()
            try {
                val request = Request.Builder().url(release.assetUrl).get().build()
                httpClient.newCall(request).execute().use { response ->
                    check(response.isSuccessful) { "Update download HTTP ${response.code}" }
                    val finalUrl = response.request.url
                    check(finalUrl.isHttps && TrustedUpdate.allowedFinalHost(finalUrl.host)) {
                        "Update download redirected to an untrusted host"
                    }
                    val body = checkNotNull(response.body) { "Empty update response" }
                    val advertised = body.contentLength()
                    check(advertised < 0 || advertised == release.assetSize) {
                        "Update Content-Length does not match release metadata"
                    }
                    val digest = MessageDigest.getInstance("SHA-256")
                    var total = 0L
                    val buffer = ByteArray(64 * 1024)
                    staging.outputStream().buffered().use { output ->
                        body.byteStream().use { input ->
                            while (true) {
                                coroutineContext.ensureActive()
                                val read = input.read(buffer)
                                if (read < 0) break
                                total += read
                                check(total <= release.assetSize && total <= TrustedUpdate.MAX_APK_BYTES) {
                                    "Update download exceeded its declared size"
                                }
                                output.write(buffer, 0, read)
                                digest.update(buffer, 0, read)
                                onProgress(total.toFloat() / release.assetSize)
                            }
                        }
                    }
                    check(total == release.assetSize) { "Update download truncated" }
                    check(TrustedUpdate.hex(digest.digest()) == expected) { "Update checksum mismatch" }
                }
                val parsed = context.packageManager.getPackageArchiveInfo(staging.absolutePath, 0)
                check(parsed?.packageName == context.packageName) {
                    "Update APK package name does not match this application"
                }
                check(!apk.exists() || apk.delete()) { "Cannot replace old verified APK" }
                check(staging.renameTo(apk)) { "Cannot publish verified APK" }
                context.cacheDir.listFiles()?.filter {
                    it != apk && it.name.startsWith("cinderbox_update_") && it.name.endsWith(".apk")
                }?.forEach { it.delete() }
                AppLogger.i(TAG, "Verified app update: ${apk.length()} bytes")
                apk
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) throw e
                AppLogger.e(TAG, "App update verification failed", e)
                null
            } finally {
                staging.delete()
            }
        }
}
