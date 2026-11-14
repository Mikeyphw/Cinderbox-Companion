package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** Pure JVM: no Android filesystem, Nexus network, game state or credentials. */
class NexusPairingAuthorityCacheTest {
    private fun awaitValue(cache: NexusPairingAuthorityCache, revision: Long, expected: String): Boolean {
        val until = System.currentTimeMillis() + 3000L
        while (System.currentTimeMillis() < until) {
            if (cache.getOrLaunch(emptyList(), revision, System.currentTimeMillis()) == expected) return true
            Thread.sleep(10)
        }
        return false
    }

    @Test fun blockedInventoryDoesNotBlockAuthenticatedState() {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val sequence = AtomicInteger()
        val cache = NexusPairingAuthorityCache { _, _ ->
            val current = sequence.incrementAndGet()
            if (current == 1) {
                entered.countDown()
                release.await(4, TimeUnit.SECONDS)
            }
            if (current == 1) "OLD_SESSION_EVIDENCE" else "NEW_SESSION_EVIDENCE"
        }
        val start = System.nanoTime()
        assertNull(cache.getOrLaunch(emptyList(), 3L, System.currentTimeMillis()))
        val elapsedMs = (System.nanoTime() - start) / 1_000_000L
        assertTrue("Inventory scheduling blocked the caller", elapsedMs < 1500L)
        assertTrue(entered.await(2, TimeUnit.SECONDS))
        cache.invalidate() // Simulates stop/revoke during an in-flight scan.
        release.countDown()
        // Stale evidence must never be published after revocation.
        assertTrue(awaitValue(cache, 4L, "NEW_SESSION_EVIDENCE"))
    }

    @Test fun journalRevisionInvalidatesWithoutFabricatingInstalledState() {
        val counter = AtomicInteger()
        val cache = NexusPairingAuthorityCache { _, _ -> "evidence-${counter.incrementAndGet()}" }
        assertNull(cache.getOrLaunch(emptyList(), 1L, System.currentTimeMillis()))
        assertTrue(awaitValue(cache, 1L, "evidence-1"))
        assertNull(cache.getOrLaunch(emptyList(), 2L, System.currentTimeMillis()))
        assertTrue(awaitValue(cache, 2L, "evidence-2"))
        assertEquals(2, counter.get())
    }

    @Test fun failedScanRemainsUnknownAndCannotPublishEvidence() {
        val runs = AtomicInteger()
        val cache = NexusPairingAuthorityCache { _, _ ->
            runs.incrementAndGet()
            throw IllegalStateException("synthetic inaccessible files")
        }
        assertNull(cache.getOrLaunch(emptyList(), 7L, System.currentTimeMillis()))
        Thread.sleep(150)
        assertNull(cache.getOrLaunch(emptyList(), 7L, System.currentTimeMillis()))
        assertTrue(runs.get() >= 1)
    }

    @Test fun concurrentCallsScheduleAtMostOneInFlightScan() {
        val counter = AtomicInteger()
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val cache = NexusPairingAuthorityCache { _, _ ->
            counter.incrementAndGet()
            entered.countDown()
            release.await(2, TimeUnit.SECONDS)
            "SAFE_EVIDENCE"
        }
        val runners = (0 until 12).map {
            Thread { repeat(4) { assertNull(cache.getOrLaunch(emptyList(), 1L, System.currentTimeMillis())) } }
        }
        runners.forEach(Thread::start)
        runners.forEach(Thread::join)
        assertTrue(entered.await(2, TimeUnit.SECONDS))
        assertEquals(1, counter.get())
        release.countDown()
        assertTrue(awaitValue(cache, 1L, "SAFE_EVIDENCE"))
    }
}
