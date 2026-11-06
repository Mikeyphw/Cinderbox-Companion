package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

/** No Android service, root, Shizuku app, private data or real Mods files required. */
class GameSessionPrivilegedProviderTest {
    @Test fun shizukuRunningDoesNotRequestRoot() {
        var rootCalls = 0
        val observation = GameSessionSafety.fromProviders(40) {
            rootCalls++
            GameSessionObservation.NOT_OBSERVED
        }
        assertEquals(GameSessionObservation.RUNNING, observation)
        assertEquals(0, rootCalls)
    }

    @Test fun shizukuNotObservedDoesNotRequestRootOrPermitWrite() {
        var rootCalls = 0
        val observation = GameSessionSafety.fromProviders(41) {
            rootCalls++
            GameSessionObservation.RUNNING
        }
        assertEquals(GameSessionObservation.NOT_OBSERVED, observation)
        assertEquals(0, rootCalls)
        assertFalse(GameSessionSafety.permitsLiveBulkWrite(observation))
    }

    @Test fun missingServiceFallsBackToRootExactlyOnce() {
        var rootCalls = 0
        val observation = GameSessionSafety.fromProviders(null) {
            rootCalls++
            GameSessionObservation.RUNNING
        }
        assertEquals(GameSessionObservation.RUNNING, observation)
        assertEquals(1, rootCalls)
    }

    @Test fun invalidServiceResultFallsBackAndDoesNotGrantAccess() {
        var rootCalls = 0
        for (code in listOf(0, 1, -1, 72, 73, 74, 75, 126)) {
            val observation = GameSessionSafety.fromProviders(code) {
                rootCalls++
                GameSessionObservation.UNKNOWN
            }
            assertEquals(GameSessionObservation.UNKNOWN, observation)
            assertFalse(GameSessionSafety.permitsLiveBulkWrite(observation))
        }
        assertEquals(8, rootCalls)
    }

    @Test fun noProviderCanMakeWritesPermissible() {
        for (code in listOf(null, 40, 41, 0, 75)) {
            val observation = GameSessionSafety.fromProviders(code) {
                GameSessionObservation.NOT_OBSERVED
            }
            assertFalse(GameSessionSafety.permitsLiveBulkWrite(observation))
        }
    }
}
