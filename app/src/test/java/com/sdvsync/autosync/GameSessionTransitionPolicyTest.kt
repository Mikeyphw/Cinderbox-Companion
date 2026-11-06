package com.sdvsync.autosync

import com.sdvsync.mods.GameSessionObservation.*
import org.junit.Assert.*
import org.junit.Test

/** Pure JVM tests: no root, game, Android device, or filesystem writes. */
class GameSessionTransitionPolicyTest {
    private val none = GameSessionTransition.NONE
    private val started = GameSessionTransition.STARTED
    private val stopped = GameSessionTransition.STOP_CANDIDATE_CONFIRMED

    @Test fun initialAbsenceNeverTriggersAutoSync() {
        val p = GameSessionTransitionPolicy()
        repeat(10) { assertEquals(none, p.advance(NOT_OBSERVED)) }
    }
    @Test fun initialUnknownNeverLooksLikeStopped() {
        val p = GameSessionTransitionPolicy()
        repeat(10) { assertEquals(none, p.advance(UNKNOWN)) }
    }
    @Test fun oneAbsenceAfterRunningIsNotEnough() {
        val p = GameSessionTransitionPolicy()
        assertEquals(started, p.advance(RUNNING))
        assertEquals(none, p.advance(NOT_OBSERVED))
    }
    @Test fun twoConsecutiveAbsencesRequireARecheck() {
        val p = GameSessionTransitionPolicy()
        assertEquals(started, p.advance(RUNNING))
        assertEquals(none, p.advance(NOT_OBSERVED))
        assertEquals(stopped, p.advance(NOT_OBSERVED))
    }
    @Test fun unknownInterruptsAbsenceSequence() {
        val p = GameSessionTransitionPolicy()
        p.advance(RUNNING)
        assertEquals(none, p.advance(NOT_OBSERVED))
        assertEquals(none, p.advance(UNKNOWN))
        assertEquals(none, p.advance(NOT_OBSERVED))
        assertEquals(stopped, p.advance(NOT_OBSERVED))
    }
    @Test fun runningResetsStopCandidateAndDoesNotDuplicateStart() {
        val p = GameSessionTransitionPolicy()
        assertEquals(started, p.advance(RUNNING))
        p.advance(NOT_OBSERVED)
        assertEquals(none, p.advance(RUNNING))
        assertEquals(none, p.advance(NOT_OBSERVED))
        assertEquals(stopped, p.advance(NOT_OBSERVED))
    }
    @Test fun secondStopRequiresAnotherDefiniteStart() {
        val p = GameSessionTransitionPolicy()
        p.advance(RUNNING); p.advance(NOT_OBSERVED); p.advance(NOT_OBSERVED)
        assertEquals(none, p.advance(NOT_OBSERVED))
        assertEquals(started, p.advance(RUNNING))
        assertEquals(none, p.advance(NOT_OBSERVED))
        assertEquals(stopped, p.advance(NOT_OBSERVED))
    }
    @Test fun unknownAfterStopDoesNotSignalNewStart() {
        val p = GameSessionTransitionPolicy()
        p.advance(RUNNING); p.advance(NOT_OBSERVED); p.advance(NOT_OBSERVED)
        assertEquals(none, p.advance(UNKNOWN))
        assertEquals(none, p.advance(NOT_OBSERVED))
    }
}
