package com.sdvsync.autosync

import com.sdvsync.mods.GameSessionObservation
import com.sdvsync.mods.GameSessionProbe
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Observe the game using a bounded root probe. UNKNOWN is never interpreted as stopped.
 * This monitor is for auto-sync notifications, NOT for approving Mods writes.
 */
class GameProcessMonitor {
    companion object { private const val POLL_INTERVAL_MS = 5000L }

    private val _isGameRunning = MutableStateFlow(true) // unknown is conservatively busy
    val isGameRunning: StateFlow<Boolean> = _isGameRunning.asStateFlow()
    private val _gameSessionStatus = MutableStateFlow(GameSessionObservation.UNKNOWN)
    val gameSessionStatus: StateFlow<GameSessionObservation> = _gameSessionStatus.asStateFlow()
    private var monitorJob: Job? = null

    fun start(onGameStarted: () -> Unit = {}, onGameStopped: () -> Unit = {}) {
        if (monitorJob != null) return
        monitorJob = CoroutineScope(Dispatchers.IO).launch {
            val transitions = GameSessionTransitionPolicy()
            while (isActive) {
                val observation = GameSessionProbe().observe()
                publish(observation)
                when (transitions.advance(observation)) {
                    GameSessionTransition.STARTED -> onGameStarted()
                    GameSessionTransition.STOP_CANDIDATE_CONFIRMED -> {
                        // Do not call onGameStopped based on an old point-in-time sample.
                        delay(3000L)
                        val rechecked = GameSessionProbe().observe()
                        publish(rechecked)
                        // A new start or failed probe cancels this stop; never sync on UNKNOWN.
                        if (rechecked == GameSessionObservation.NOT_OBSERVED) {
                            onGameStopped()
                        } else if (transitions.advance(rechecked) == GameSessionTransition.STARTED) {
                            onGameStarted()
                        }
                    }
                    GameSessionTransition.NONE -> Unit
                }
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    private fun publish(observation: GameSessionObservation) {
        _gameSessionStatus.value = observation
        // A Boolean cannot represent UNKNOWN. Favor no potentially unsafe sync.
        _isGameRunning.value = observation != GameSessionObservation.NOT_OBSERVED
    }

    fun stop() {
        monitorJob?.cancel()
        monitorJob = null
        publish(GameSessionObservation.UNKNOWN)
    }
}
