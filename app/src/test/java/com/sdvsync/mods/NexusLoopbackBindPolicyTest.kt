package com.sdvsync.mods

import java.net.BindException
import java.net.SocketException
import org.junit.Assert.*
import org.junit.Test

class NexusLoopbackBindPolicyTest {
    @Test fun transientBindConflictRetriesWithinFiniteBudget() {
        var calls = 0
        val delays = mutableListOf<Long>()
        val result = NexusLoopbackBindPolicy.acquire({
            calls++
            if (calls < 3) throw BindException("simulated conflict")
            "BOUND"
        }, { delays += it })
        assertEquals("BOUND", result)
        assertEquals(3, calls)
        assertEquals(listOf(90L, 90L), delays)
    }

    @Test fun persistentBindConflictFailsClosedAfterFiveAttempts() {
        var calls = 0
        var sleeps = 0
        try {
            NexusLoopbackBindPolicy.acquire({
                calls++
                throw BindException("simulated persistent conflict")
            }, { sleeps++ })
            fail("Fail-open: persistent conflict")
        } catch (_: BindException) {
            assertEquals(5, calls)
            assertEquals(4, sleeps)
        }
    }

    @Test fun nonBindSocketFailureIsNeverRetried() {
        var calls = 0
        try {
            NexusLoopbackBindPolicy.acquire({
                calls++
                throw SocketException("simulated transport failure")
            }, { fail("Unexpected retry") })
            fail("Fail-open: unrelated socket failure")
        } catch (_: SocketException) {
            assertEquals(1, calls)
        }
    }

    @Test fun interruptedRetryPropagatesWithoutSwallowing() {
        var calls = 0
        try {
            NexusLoopbackBindPolicy.acquire({
                calls++
                throw BindException("simulated conflict")
            }, { throw InterruptedException("synthetic interruption") })
            fail("Fail-open: interrupted retry")
        } catch (_: InterruptedException) {
            assertEquals(1, calls)
        }
    }
}
