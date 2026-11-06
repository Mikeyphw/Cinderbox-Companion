package com.sdvsync.mods

import android.os.Bundle
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.fileaccess.ShizukuFileAccess
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Fixed-target read-only diagnostics. Never touches Mods, saves, or account credentials. */
@RunWith(AndroidJUnit4::class)
class GameSessionDeviceProbeTest {
    private fun receipt(provider: String, observation: GameSessionObservation) {
        val safe = if (observation == GameSessionObservation.UNKNOWN) "INCONCLUSIVE" else "OBSERVED"
        val bundle = Bundle().apply {
            putString("R2E_PROVIDER", provider)
            putString("R2E_RESULT", safe)
            putString("R2E_GAME", observation.name)
            putString("R2E_LIVE_MOD_WRITES", "DISABLED")
        }
        InstrumentationRegistry.getInstrumentation().sendStatus(0, bundle)
    }

    @Test fun policyOnlyDoesNotAccessPrivilegedServices() {
        GameSessionObservation.entries.forEach {
            assertFalse(GameSessionSafety.permitsLiveBulkWrite(it))
        }
        receipt("POLICY", GameSessionObservation.UNKNOWN)
    }

    /** Physical-device opt-in test. Shizuku may be unavailable or ungranted. */
    @Test fun shizukuReadOnlyDiagnostic() = runBlocking {
        val code = runCatching { ShizukuFileAccess.queryGameStatus() }.getOrNull()
        val observed = GameSessionSafety.fromRootProbeExit(code)
        receipt("SHIZUKU", observed)
        assertFalse(GameSessionSafety.permitsLiveBulkWrite(observed))
    }

    /** Physical-device opt-in test. su may prompt; an unknown result is inconclusive. */
    @Test fun rootReadOnlyDiagnostic() {
        val observed = GameSessionProbe().observe()
        receipt("ROOT", observed)
        assertFalse(GameSessionSafety.permitsLiveBulkWrite(observed))
    }
}
