package com.sdvsync.mods

/** Pure, credential-free control policy. Transfer URLs are never kept in the journal. */
object ModQueueControlPolicy {
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    fun canPause(status: String) = status == "QUEUED" || status == "DOWNLOADING"
    fun canCancel(status: String) = status == "QUEUED" || status == "DOWNLOADING" || status == "PAUSED"
    fun canResumeInSession(status: String) = status == "PAUSED"
    fun validMove(index: Int, count: Int, delta: Int): Boolean =
        (delta == -1 || delta == 1) && index >= 0 && index < count && index + delta in 0 until count
    fun freshLinkAllowed(source: String, modId: String, fileId: String, status: String): Boolean =
        source == "nexus" && positiveId.matches(modId) && positiveId.matches(fileId) &&
            status in setOf("INTERRUPTED", "FAILED", "CANCELLED")
}
