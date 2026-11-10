package com.sdvsync.mods

/**
 * Single-flight, fail-closed cache for expensive LOCAL inventory observation.
 * Never executes filesystem work on the authenticated HTTP server thread.
 * A stopped/revoked session or changed journal revision invalidates older results.
 * No credentials or paths are retained in this cache.
 */
internal class NexusPairingAuthorityCache(
    private val compute: (List<ModDownloadRecord>, Long) -> String
) {
    private val lock = Any()
    private var generation = 0L
    private var sourceRevision: Long? = null
    private var inFlight = false
    private var data: String? = null
    private var publishedAtMs = 0L
    private val MAX_AGE_MS = 15_000L

    fun invalidate(): Unit = synchronized(lock) {
        generation++
        sourceRevision = null
        data = null
        publishedAtMs = 0L
        // Do not reset inFlight: a filesystem operation may be blocked. At most
        // ONE worker is permitted; an outdated worker must never publish.
    }

    /** A null result means REFRESHING/UNKNOWN, never proof of empty installed mods. */
    fun getOrLaunch(
        records: List<ModDownloadRecord>, revision: Long, observedAtMs: Long
    ): String? = synchronized(lock) {
        if (sourceRevision != revision) {
            generation++
            sourceRevision = revision
            data = null
            publishedAtMs = 0L
        }
        val fresh = data != null && observedAtMs >= publishedAtMs &&
            observedAtMs - publishedAtMs <= MAX_AGE_MS
        if (fresh) return@synchronized data
        data = null // Never expose expired observations while a refresh is running.
        if (!inFlight) {
            inFlight = true
            val requestGeneration = generation
            val snapshot = records.toList() // Immutable journal evidence for this scan.
            Thread({
                val result = try { compute(snapshot, System.currentTimeMillis()) }
                    catch (_: Exception) { null }
                synchronized(lock) {
                    inFlight = false
                    if (requestGeneration == generation) {
                        data = result
                        publishedAtMs = System.currentTimeMillis()
                    }
                }
            }, "cbnx04-inventory-readonly").apply {
                isDaemon = true
                start()
            }
        }
        null
    }
}
