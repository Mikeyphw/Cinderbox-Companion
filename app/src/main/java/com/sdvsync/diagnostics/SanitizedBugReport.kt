package com.sdvsync.diagnostics

import android.os.Build
import com.sdvsync.BuildConfig
import com.sdvsync.steam.SteamDiagnostics
import org.json.JSONArray
import org.json.JSONObject

/** Strict-schema export: no log text, stacktraces, save names, account data, or network addresses. */
object SanitizedBugReport {
    fun exportJson(): String {
        val events = JSONArray()
        SyncOperationDiagnostics.snapshot().forEach { e ->
            events.put(JSONObject().put("direction", e.direction.name)
                .put("outcome", e.outcome.name).put("error_code", e.errorCode))
        }
        val steam = SteamDiagnostics.snapshot.value
        return JSONObject().put("schema_version", 1)
            .put("producer", "cinderbox-companion")
            .put("app_version", BuildConfig.VERSION_NAME)
            .put("app_version_code", BuildConfig.VERSION_CODE)
            .put("android_api", Build.VERSION.SDK_INT)
            .put("network", SteamDiagnostics.networkSummary())
            .put("steam_phase", steam.phase.name)
            .put("steam_failure_count", steam.failures)
            .put("steam_transport", SteamDiagnostics.activeTransport)
            .put("sync_operations", events)
            .toString(2)
    }
}
