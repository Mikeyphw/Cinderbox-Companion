package com.sdvsync.steam

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.Job
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SavedSessionReconnectRunnerTest {
    @Test
    fun `logout cancels network wait before any login`() = runBlocking {
        var attempts = 0
        val waiting = CompletableDeferred<Unit>()
        val neverAvailable = CompletableDeferred<Unit>()
        val retry = async {
            runSavedSessionReconnect(
                pause = {},
                awaitNetwork = { waiting.complete(Unit); neverAvailable.await() },
                attempt = { attempts++ },
                connected = { false },
                canRetry = { true }
            )
        }
        waiting.await()
        retry.cancel()
        retry.join()
        assertTrue(retry.isCancelled)
        assertEquals(0, attempts)
    }

    @Test
    fun `network unavailability suspends without consuming attempts`() = runBlocking {
        var attempts = 0
        var connected = false
        val waiting = CompletableDeferred<Unit>()
        val network = CompletableDeferred<Unit>()
        val result = async {
            runSavedSessionReconnect(
                pause = {},
                awaitNetwork = {
                    waiting.complete(Unit)
                    network.await()
                },
                attempt = { attempts++; connected = true },
                connected = { connected },
                canRetry = { true }
            )
        }
        waiting.await()
        assertEquals(0, attempts)
        network.complete(Unit)
        assertTrue(result.await())
        assertEquals(1, attempts)
    }

    @Test
    fun `cancelling an individual login does not cancel subsequent retries`() = runBlocking {
        val waits = mutableListOf<Long>()
        val results = mutableListOf<Pair<Int, Boolean>>()
        var attempts = 0
        var connected = false
        val recovered = runSavedSessionReconnect(
            pause = { waits += it },
            attempt = {
                attempts++
                if (attempts < 3) {
                    currentCoroutineContext()[Job]!!.cancel()
                } else {
                    connected = true
                }
            },
            connected = { connected },
            canRetry = { true },
            onResult = { index, ok -> results += index to ok }
        )
        assertTrue(recovered)
        assertEquals(3, attempts)
        assertEquals(listOf(2_000L, 4_000L, 8_000L), waits)
        assertEquals(listOf(1 to false, 2 to false, 3 to true), results)
    }

    @Test
    fun `six failed children exhaust only the bounded retry loop`() = runBlocking {
        var attempts = 0
        val result = runSavedSessionReconnect(
            pause = {},
            attempt = { attempts++; currentCoroutineContext()[Job]!!.cancel() },
            connected = { false },
            canRetry = { true }
        )
        assertFalse(result)
        assertEquals(6, attempts)
    }

    @Test
    fun `logout during backoff prevents a new login`() = runBlocking {
        var signedIn = true
        var attempts = 0
        val result = runSavedSessionReconnect(
            pause = { signedIn = false },
            attempt = { attempts++ },
            connected = { false },
            canRetry = { signedIn }
        )
        assertFalse(result)
        assertEquals(0, attempts)
    }
}
