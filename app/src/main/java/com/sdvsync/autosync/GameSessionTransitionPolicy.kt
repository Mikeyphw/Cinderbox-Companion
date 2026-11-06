package com.sdvsync.autosync

import com.sdvsync.mods.GameSessionObservation

/** Pure observer transition model; a NOT_OBSERVED sample is not game-idle proof. */
internal enum class GameSessionTransition { NONE, STARTED, STOP_CANDIDATE_CONFIRMED }

/**
 * Only a previous definite RUNNING followed by two consecutive definitive absences
 * can request a stop recheck. UNKNOWN invalidates the candidate; callbacks are gated
 * by a fresh independent process observation in GameProcessMonitor.
 */
internal class GameSessionTransitionPolicy {
    private var seenRunning = false
    private var absentCount = 0

    fun advance(observation: GameSessionObservation): GameSessionTransition = when (observation) {
        GameSessionObservation.RUNNING -> {
            absentCount = 0
            if (!seenRunning) {
                seenRunning = true
                GameSessionTransition.STARTED
            } else GameSessionTransition.NONE
        }
        GameSessionObservation.UNKNOWN -> {
            absentCount = 0
            GameSessionTransition.NONE
        }
        GameSessionObservation.NOT_OBSERVED -> {
            if (!seenRunning) GameSessionTransition.NONE
            else if (++absentCount < 2) GameSessionTransition.NONE
            else {
                seenRunning = false
                absentCount = 0
                GameSessionTransition.STOP_CANDIDATE_CONFIRMED
            }
        }
    }
}
