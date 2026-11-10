package com.sdvsync.mods

import java.net.BindException

/**
 * Bounded workaround for transient loopback port reuse after an explicit close.
 * Never retries unrelated errors and NEVER changes the listening address.
 */
internal object NexusLoopbackBindPolicy {
    const val MAX_ATTEMPTS = 5
    const val BACKOFF_MS = 90L

    fun <T> acquire(bind: () -> T, pause: (Long) -> Unit = { Thread.sleep(it) }): T {
        for (attempt in 1..MAX_ATTEMPTS) {
            try {
                return bind()
            } catch (error: BindException) {
                if (attempt == MAX_ATTEMPTS) throw error
                pause(BACKOFF_MS)
            }
        }
        throw IllegalStateException("Unreachable loopback bind retry state")
    }
}
