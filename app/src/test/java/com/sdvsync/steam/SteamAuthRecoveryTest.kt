package com.sdvsync.steam

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SteamAuthRecoveryTest {
    @Test
    fun `orphaned interactive authentication states must become visible disconnect errors`() {
        assertTrue(shouldRecoverOrphanedAuthState(AuthState.Connecting))
        assertTrue(shouldRecoverOrphanedAuthState(AuthState.Authenticating))
        assertTrue(shouldRecoverOrphanedAuthState(AuthState.LoggingIn))
        assertTrue(shouldRecoverOrphanedAuthState(AuthState.WaitingFor2FA(is2FACode = false)))
        assertTrue(shouldRecoverOrphanedAuthState(AuthState.WaitingForDeviceConfirmation(canUseCode = true)))
        assertTrue(shouldRecoverOrphanedAuthState(AuthState.WaitingForQRScan("test-only")))
    }

    @Test
    fun `completed and error states are not overwritten by stale transport callbacks`() {
        assertFalse(shouldRecoverOrphanedAuthState(AuthState.Idle))
        assertFalse(shouldRecoverOrphanedAuthState(AuthState.LoggedIn))
        assertFalse(shouldRecoverOrphanedAuthState(AuthState.Error("already failed")))
    }
}
