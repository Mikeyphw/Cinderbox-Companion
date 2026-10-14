package com.sdvsync.steam

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.supervisorScope

/**
 * A bounded retry policy whose owner is independent of individual authentication attempts.
 * AuthAttemptCoordinator is allowed to cancel a failed attempt without cancelling this owner.
 * Never starts an attempt after logout or once a session has successfully recovered.
 */
internal suspend fun runSavedSessionReconnect(
    pause: suspend (Long) -> Unit,
    attempt: suspend () -> Unit,
    connected: () -> Boolean,
    canRetry: () -> Boolean,
    onWaiting: (Int) -> Unit = {},
    onResult: (Int, Boolean) -> Unit = { _, _ -> }
): Boolean {
    var backoffMs = 2_000L
    for (number in 1..6) {
        if (!canRetry() || connected()) return connected()
        onWaiting(number)
        pause(backoffMs)
        if (!canRetry() || connected()) return connected()

        // Child failure/cancellation must not cancel the enclosing retry controller.
        // A deliberately cancelled individual auth attempt is an expected recoverable result.
        supervisorScope {
            launch {
                try {
                    attempt()
                } catch (_: CancellationException) {
                    // AuthAttemptCoordinator cancelled this child; owner stays alive.
                } catch (_: Exception) {
                    // No remote message or credential data is captured in diagnostics.
                }
            }.join()
        }
        val ok = connected()
        onResult(number, ok)
        if (ok || !canRetry()) return ok
        backoffMs = (backoffMs * 2).coerceAtMost(30_000L)
    }
    return connected()
}
