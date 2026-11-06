package com.sdvsync.ui.policy

import org.junit.Assert.assertEquals
import org.junit.Test

class SteamCapabilityGateTest {
    @Test fun disconnectedUserCannotDownload() {
        val c = SteamCapabilities(false, true, true, true)
        assertEquals(SteamAccessResult.SIGN_IN_REQUIRED, SteamCapabilityGate.gameDownload(c))
        assertEquals(SteamAccessResult.SIGN_IN_REQUIRED, SteamCapabilityGate.cloudSaves(c))
        assertEquals(SteamAccessResult.SIGN_IN_REQUIRED, SteamCapabilityGate.cloudSync(c))
    }

    @Test fun loggedInDoesNotProveGameEntitlement() {
        val c = SteamCapabilities(true, false, true, true)
        assertEquals(SteamAccessResult.ENTITLEMENT_UNVERIFIED, SteamCapabilityGate.gameDownload(c))
    }

    @Test fun offlineSteamCannotDownload() {
        val c = SteamCapabilities(true, true, false, false)
        assertEquals(SteamAccessResult.NETWORK_UNAVAILABLE, SteamCapabilityGate.gameDownload(c))
        assertEquals(SteamAccessResult.NETWORK_UNAVAILABLE, SteamCapabilityGate.cloudSaves(c))
    }

    @Test fun authenticatedUserNeedsCloudAvailability() {
        val c = SteamCapabilities(true, true, true, false)
        assertEquals(SteamAccessResult.CLOUD_UNAVAILABLE, SteamCapabilityGate.cloudSaves(c))
    }

    @Test fun eligibleStateStillRequiresExistingOperationGuards() {
        val c = SteamCapabilities(true, true, true, true)
        assertEquals(SteamAccessResult.AVAILABLE_FOR_FURTHER_CHECKS, SteamCapabilityGate.gameDownload(c))
    }
}
