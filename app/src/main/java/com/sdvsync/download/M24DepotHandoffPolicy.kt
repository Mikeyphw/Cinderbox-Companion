package com.sdvsync.download

/** No network or filesystem access. Labels are constants, never raw SDK messages. */
object M24DepotHandoffPolicy {
    const val FIRST_CONTENT_TIMEOUT_MS = 240_000L
    const val TRANSFER_STALL_TIMEOUT_MS = 300_000L

    fun safePhase(sdkMessage: String): String? = when {
        sdkMessage.startsWith("Downloading manifest for depot ") -> "Fetching Steam depot manifest…"
        sdkMessage.startsWith("Allocating file: ") -> "Allocating Steam depot files…"
        sdkMessage.startsWith("Validating: ") -> "Checking existing Steam depot chunks…"
        else -> null // Never surface filenames, account identifiers, URLs or tokens.
    }

    /** Failure reason is a constant suitable for machine-readable device evidence. */
    fun failureCode(nowMs: Long, startMs: Long, lastContentMs: Long,
                    contentObserved: Boolean, downloadFailed: Boolean): String? {
        if (downloadFailed) return "STEAM_DEPOT_REPORTED_FAILURE"
        if (!contentObserved && nowMs - startMs >= FIRST_CONTENT_TIMEOUT_MS) {
            return "STEAM_DEPOT_FIRST_CONTENT_TIMEOUT"
        }
        if (contentObserved && nowMs - lastContentMs >= TRANSFER_STALL_TIMEOUT_MS) {
            return "STEAM_DEPOT_CONTENT_STALLED"
        }
        return null
    }
}
