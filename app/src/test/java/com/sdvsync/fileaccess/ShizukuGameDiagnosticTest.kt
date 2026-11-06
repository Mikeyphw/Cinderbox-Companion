package com.sdvsync.fileaccess

import org.junit.Assert.*
import org.junit.Test

/** Pure Kotlin/JVM, no privileged access, Android services or real game files. */
class ShizukuGameDiagnosticTest {
    @Test fun runningCodeIsRecognized() {
        assertEquals(ShizukuGameDiagnostic.RUNNING, ShizukuDiagnosticPolicy.fromProcessCode(40))
        assertEquals(40, ShizukuGameDiagnostic.RUNNING.processCode)
    }
    @Test fun absenceCodeIsRecognizedButNotAuthorization() {
        assertEquals(ShizukuGameDiagnostic.NOT_OBSERVED, ShizukuDiagnosticPolicy.fromProcessCode(41))
        assertEquals(41, ShizukuGameDiagnostic.NOT_OBSERVED.processCode)
    }
    @Test fun unknownCodesCannotPretendToBeAbsence() {
        listOf(null, 0, 1, 2, -1, 39, 42, 70, 71, 72, 73, 74, 75, 126, 127).forEach {
            assertEquals(ShizukuGameDiagnostic.PROCESS_UNKNOWN, ShizukuDiagnosticPolicy.fromProcessCode(it))
        }
    }
    @Test fun allDiagnosticErrorsHaveNoProcessCode() {
        ShizukuGameDiagnostic.entries.filterNot {
            it == ShizukuGameDiagnostic.RUNNING || it == ShizukuGameDiagnostic.NOT_OBSERVED
        }.forEach { assertNull(it.processCode) }
    }
    @Test fun transientServiceTimeoutCanRetry() {
        assertTrue(ShizukuDiagnosticPolicy.shouldRetryConnection(ShizukuGameDiagnostic.SERVICE_TIMEOUT))
    }
    @Test fun transientBinderDisconnectCanRetry() {
        assertTrue(ShizukuDiagnosticPolicy.shouldRetryConnection(ShizukuGameDiagnostic.SERVICE_DISCONNECTED))
    }
    @Test fun serviceBindErrorCanRetryOnce() {
        assertTrue(ShizukuDiagnosticPolicy.shouldRetryConnection(ShizukuGameDiagnostic.SERVICE_BIND_FAILED))
    }
    @Test fun authorizationFailuresDoNotRetryAutomatically() {
        listOf(ShizukuGameDiagnostic.PERMISSION_DENIED,
            ShizukuGameDiagnostic.PERMISSION_CHECK_FAILED,
            ShizukuGameDiagnostic.BINDER_NOT_READY).forEach {
            assertFalse(ShizukuDiagnosticPolicy.shouldRetryConnection(it))
        }
    }
    @Test fun processResultsDoNotRetryAutomatically() {
        listOf(ShizukuGameDiagnostic.RUNNING, ShizukuGameDiagnostic.NOT_OBSERVED,
            ShizukuGameDiagnostic.PROCESS_UNKNOWN).forEach {
            assertFalse(ShizukuDiagnosticPolicy.shouldRetryConnection(it))
        }
    }
    @Test fun remoteCallErrorsAreNotSilentlyRetriggered() {
        assertFalse(ShizukuDiagnosticPolicy.shouldRetryConnection(ShizukuGameDiagnostic.REMOTE_CALL_FAILED))
    }
}
