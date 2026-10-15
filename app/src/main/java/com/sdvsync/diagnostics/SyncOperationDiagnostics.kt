package com.sdvsync.diagnostics
import java.util.ArrayDeque

/** In-memory, fixed-vocabulary sync telemetry; no file names, raw errors, user IDs or URLs. */
enum class SyncTelemetryDirection { PULL, PUSH }
enum class SyncTelemetryOutcome { SUCCESS, ERROR, CONFLICT, STALE_PREVIEW }

data class SyncTelemetryEvent(val direction: SyncTelemetryDirection,
                              val outcome: SyncTelemetryOutcome, val errorCode: String)

object SyncOperationDiagnostics {
    private val events = ArrayDeque<SyncTelemetryEvent>()
    private val lock = Any()
    private const val MAX_EVENTS = 48
    private val allowedErrors = setOf("NONE", "NO_CLOUD_FILES", "INVALID_DOWNLOAD",
        "WRITE_FAILED", "NETWORK_ERROR", "NO_LOCAL_FILES", "SAVE_IN_PROGRESS",
        "INVALID_LOCAL", "BACKUP_FAILED", "LOCAL_NEWER", "CLOUD_NEWER", "UNKNOWN")

    fun record(direction: SyncTelemetryDirection, outcome: SyncTelemetryOutcome, errorCode: String = "NONE") {
        val safeCode = if (errorCode in allowedErrors) errorCode else "UNKNOWN"
        synchronized(lock) {
            if (events.size >= MAX_EVENTS) events.removeFirst()
            events.addLast(SyncTelemetryEvent(direction, outcome, safeCode))
        }
    }
    fun snapshot(): List<SyncTelemetryEvent> = synchronized(lock) { events.toList() }
}
