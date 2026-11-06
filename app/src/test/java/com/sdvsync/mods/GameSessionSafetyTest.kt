package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

/** Host/JVM only. Never requests root or touches a user's Mods directory. */
class GameSessionSafetyTest {
    @Test fun observedProcessIsRunning() {
        assertEquals(GameSessionObservation.RUNNING, GameSessionSafety.fromRootProbeExit(40))
    }

    @Test fun notObservedIsNotAuthorization() {
        val observation = GameSessionSafety.fromRootProbeExit(41)
        assertEquals(GameSessionObservation.NOT_OBSERVED, observation)
        assertFalse(GameSessionSafety.permitsLiveBulkWrite(observation))
    }

    @Test fun rootDeniedOrUnknownCodeFailsClosed() {
        for (code in listOf(null, -1, 0, 1, 71, 72, 73, 74, 75, 126, 127)) {
            assertEquals(GameSessionObservation.UNKNOWN, GameSessionSafety.fromRootProbeExit(code))
        }
    }

    @Test fun noneOfTheThreeStatesPermitsLiveWrites() {
        GameSessionObservation.entries.forEach {
            assertFalse(GameSessionSafety.permitsLiveBulkWrite(it))
        }
    }

    @Test fun probeIsNotRunUntilObserveIsCalled() {
        var calls = 0
        val probe = GameSessionProbe { calls++; 40 }
        assertEquals(0, calls)
        assertEquals(GameSessionObservation.RUNNING, probe.observe())
        assertEquals(1, calls)
    }

    @Test fun throwingProcessProbeFailsClosedWithoutDetails() {
        val probe = GameSessionProbe { throw IllegalStateException("sensitive local output") }
        assertEquals(GameSessionObservation.UNKNOWN, probe.observe())
        assertFalse(probe.observe().explanation.contains("sensitive"))
    }

    @Test fun singleObservationDoesNotReuseAStaleResult() {
        var code = 41
        val probe = GameSessionProbe { code }
        assertEquals(GameSessionObservation.NOT_OBSERVED, probe.observe())
        code = 40
        assertEquals(GameSessionObservation.RUNNING, probe.observe())
    }

    @Test fun diagnosticTextDoesNotClaimSafety() {
        assertTrue(GameSessionObservation.NOT_OBSERVED.explanation.contains("NOT established"))
        assertTrue(GameSessionObservation.UNKNOWN.explanation.contains("blocked"))
    }
}
