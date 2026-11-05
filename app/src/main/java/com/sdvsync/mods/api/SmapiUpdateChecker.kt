package com.sdvsync.mods.api

import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.ModUpdatePolicy
import com.sdvsync.mods.UpdateAssessment
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModUpdateInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

/**
 * Checks for mod updates via the SMAPI web API.
 * No authentication required.
 */
class SmapiUpdateChecker(private val httpClient: OkHttpClient) {
    companion object {
        private const val TAG = "SmapiUpdateChecker"
        private const val API_URL = "https://smapi.io/api/v4.0.0/mods"
    }

    /**
     * Check all installed mods for updates in a single batch request.
     * Returns a map of uniqueID -> ModUpdateInfo for mods with available updates.
     */
    suspend fun checkForUpdates(mods: List<InstalledMod>): Map<String, ModUpdateInfo> =
        checkDetailed(mods).updates

    /** Produces an explicit observation for every requested mod. */
    suspend fun checkDetailed(mods: List<InstalledMod>): com.sdvsync.mods.ModUpdateCheckResult = withContext(Dispatchers.IO) {
        if (mods.isEmpty()) return@withContext com.sdvsync.mods.ModUpdateCheckResult(
            emptyMap(), emptyMap(), System.currentTimeMillis())

        try {
            val modsArray = JSONArray()
            for (mod in mods) {
                val modObj = JSONObject().apply {
                    put("id", mod.manifest.uniqueID)
                    put("installedVersion", mod.manifest.version)
                    if (mod.manifest.updateKeys.isNotEmpty()) {
                        put("updateKeys", JSONArray(mod.manifest.updateKeys))
                    }
                }
                modsArray.put(modObj)
            }

            val body = JSONObject().apply {
                put("mods", modsArray)
                put("includeExtendedMetadata", true)
            }

            val request = Request.Builder()
                .url(API_URL)
                .post(body.toString().toRequestBody("application/json".toMediaType()))
                .build()

            val response = httpClient.newCall(request).execute()
            val responseBody = response.use {
                check(it.isSuccessful) { "SMAPI HTTP response unsuccessful" }
                it.body?.string() ?: error("SMAPI response body absent")
            }
            val results = JSONArray(responseBody)

            val result = SmapiUpdateResponseParser.parse(mods, results, System.currentTimeMillis())
            AppLogger.d(TAG, "Update check completed: ${mods.size} mods requested; " +
                "${result.updates.size} newer candidates")
            result
        } catch (e: Exception) {
            // Propagate failure. ViewModel must retain the previous cache and
            // report UNKNOWN instead of wiping actionable updates on an API outage.
            if (e is kotlinx.coroutines.CancellationException) throw e
            AppLogger.w(TAG, "SMAPI update lookup unavailable")
            throw IllegalStateException("SMAPI update lookup unavailable", e)
        }
    }

    private fun buildSourceString(mod: InstalledMod): String {
        val nexusKey = mod.manifest.updateKeys.find { it.startsWith("Nexus:", ignoreCase = true) }
        return nexusKey ?: mod.manifest.updateKeys.firstOrNull() ?: ""
    }
}
