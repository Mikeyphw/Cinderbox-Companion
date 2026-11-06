package com.sdvsync.mods

import java.util.concurrent.TimeUnit

/**
 * A process observation is diagnostic information, NOT permission to modify game files.
 * Even a root process snapshot cannot prevent Stardew from launching milliseconds later.
 */
enum class GameSessionObservation(val explanation: String) {
    RUNNING("Stardew Valley appears to be running. Keep mod files unchanged."),
    NOT_OBSERVED("No known game process was observed. Safe idle is NOT established."),
    UNKNOWN("Game status could not be independently verified. Changes remain blocked.")
}

internal object GameSessionSafety {
    fun fromRootProbeExit(exitCode: Int?): GameSessionObservation = when (exitCode) {
        40 -> GameSessionObservation.RUNNING
        41 -> GameSessionObservation.NOT_OBSERVED
        else -> GameSessionObservation.UNKNOWN
    }

    /** Do not invoke root if a privileged Shizuku UserService gave a definite result. */
    fun fromProviders(shizukuCode: Int?, rootFallback: () -> GameSessionObservation):
        GameSessionObservation {
        val shizukuObservation = fromRootProbeExit(shizukuCode)
        return if (shizukuObservation == GameSessionObservation.UNKNOWN) rootFallback()
            else shizukuObservation
    }

    /** Never make a real Mods write admissible based solely on this observation. */
    @Suppress("UNUSED_PARAMETER")
    fun permitsLiveBulkWrite(observation: GameSessionObservation): Boolean = false
}

/** Explicit user-triggered observation. No polling, auto-grant or stored credentials. */
internal class GameSessionProbe(private val exitCode: () -> Int? = { runRootProbe() }) {
    fun observe(): GameSessionObservation = GameSessionSafety.fromRootProbeExit(
        runCatching { exitCode() }.getOrNull()
    )

    companion object {
        // Fixed package name; never interpolate user-controlled text into the root command.
        // pidof and ps must BOTH work before returning an absence observation. No raw output
        // from either tool is retained or logged. 40=detected, 41=not seen, other=unknown.
        private val ROOT_PROBE = """
            uid=${'$'}(id -u 2>/dev/null) || exit 71
            [ "${'$'}uid" = 0 ] || exit 72
            pidof com.chucklefish.stardewvalley >/dev/null 2>&1
            probe_code=${'$'}?
            [ "${'$'}probe_code" = 0 ] && exit 40
            [ "${'$'}probe_code" = 1 ] || exit 73
            names=${'$'}(ps -A -o NAME 2>/dev/null) || exit 74
            printf '%s\n' "${'$'}names" | grep -E '^com[.]chucklefish[.]stardewvalley(:|${'$'})' >/dev/null 2>&1
            probe_code=${'$'}?
            [ "${'$'}probe_code" = 0 ] && exit 40
            [ "${'$'}probe_code" = 1 ] && exit 41
            exit 75
        """.trimIndent()

        private fun runRootProbe(): Int? {
            val process = runCatching {
                ProcessBuilder("su", "-c", ROOT_PROBE)
                    .redirectErrorStream(true)
                    .start()
            }.getOrNull() ?: return null
            return try {
                if (!process.waitFor(4, TimeUnit.SECONDS)) {
                    process.destroyForcibly()
                    null
                } else process.exitValue()
            } catch (_: Exception) {
                process.destroyForcibly()
                null
            } finally {
                process.destroy()
            }
        }
    }
}
