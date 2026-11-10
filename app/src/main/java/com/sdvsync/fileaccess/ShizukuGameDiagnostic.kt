package com.sdvsync.fileaccess

/** Fixed, non-sensitive Shizuku provider outcomes. No paths, PIDs or Binder exceptions. */
enum class ShizukuGameDiagnostic(val processCode: Int?) {
    RUNNING(40),
    NOT_OBSERVED(41),
    BINDER_NOT_READY(null),
    PERMISSION_DENIED(null),
    PERMISSION_CHECK_FAILED(null),
    SERVICE_BIND_FAILED(null),
    SERVICE_TIMEOUT(null),
    SERVICE_DISCONNECTED(null),
    REMOTE_CALL_FAILED(null),
    PROCESS_UNKNOWN(null)
}

/** Pure policy; intentionally never confers permission to modify any game files. */
internal object ShizukuDiagnosticPolicy {
    fun fromProcessCode(code: Int?): ShizukuGameDiagnostic = when (code) {
        40 -> ShizukuGameDiagnostic.RUNNING
        41 -> ShizukuGameDiagnostic.NOT_OBSERVED
        else -> ShizukuGameDiagnostic.PROCESS_UNKNOWN
    }

    fun shouldRetryConnection(result: ShizukuGameDiagnostic): Boolean = when (result) {
        ShizukuGameDiagnostic.SERVICE_BIND_FAILED,
        ShizukuGameDiagnostic.SERVICE_TIMEOUT,
        ShizukuGameDiagnostic.SERVICE_DISCONNECTED -> true
        else -> false
    }
}
