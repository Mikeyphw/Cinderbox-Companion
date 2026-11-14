package com.sdvsync.mods

/**
 * CB-NX05B: allowlist-only redacted local diagnostics. All output fields and statuses are
 * generated from fixed enums and counts; no free-form exception, path, ID, token, URL,
 * browser header, journal detail, credential, or remote response enters the export.
 */
internal object NexusCompanionPrivacyPolicy {
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    private val safeVersion = Regex("[0-9]{1,5}(\\.[0-9]{1,5}){0,3}(-[A-Za-z0-9]{1,16})?")
    private val requests = listOf("PENDING", "OPENED", "DISMISSED")
    private val jobs = listOf("QUEUED", "DOWNLOADING", "PAUSED", "INTERRUPTED", "FAILED",
        "CANCELLED", "VALIDATING", "REVIEW_REQUIRED", "BLOCKED", "VERIFY_REQUIRED",
        "INSTALLING", "INSTALLED", "COMPLETED", "DISCARDED")

    /** Display-only: a masked identity must never be confused with an exact-file link. */
    fun redactedId(value: String): String = if (positiveId.matches(value)) {
        if (value.length <= 4) "••••" else "••••" + value.takeLast(2)
    } else "unknown"

    fun isKnownJobStatus(value: String): Boolean = value in jobs

    fun report(appVersion: String, observedAt: Long, listening: Boolean, paired: Boolean,
               handoffAllowed: Boolean, inboxAvailable: Boolean, history: List<String>,
               journalAvailable: Boolean, statuses: List<String>): String {
        val safeAppVersion = appVersion.takeIf { safeVersion.matches(it) } ?: "unknown"
        val connection = when {
            !listening -> "NOT_LISTENING"
            paired -> "PAIRED"
            else -> "PAIRING_WINDOW"
        }
        fun counts(allowed: List<String>, values: List<String>): String = allowed.joinToString(",") {
            "\"$it\":${values.count { status -> status == it }}"
        }
        val json = "{" +
            "\"schema\":1,\"milestone\":\"CB-NX05B\",\"bridge_protocol\":1," +
            "\"app_version\":\"$safeAppVersion\",\"observed_at_ms\":${observedAt.coerceAtLeast(0L)}," +
            "\"connection\":\"$connection\",\"handoff_allowed\":${paired && listening && handoffAllowed}," +
            "\"inbox_state\":\"${if (inboxAvailable) "AVAILABLE" else "UNAVAILABLE"}\"," +
            "\"journal_state\":\"${if (journalAvailable) "AVAILABLE" else "UNAVAILABLE"}\"," +
            "\"inbox_counts\":${if (inboxAvailable) "{${counts(requests, history.take(40))}}" else "null"}," +
            "\"job_counts\":${if (journalAvailable) "{${counts(jobs, statuses.take(60))}}" else "null"}}"
        check(json.length <= 4096) { "SAFE_DIAGNOSTIC_LIMIT" }
        return json
    }
}
