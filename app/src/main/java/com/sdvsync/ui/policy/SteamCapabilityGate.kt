package com.sdvsync.ui.policy

/**
 * UX-00 UI capability presentation policy. A connected Steam UI is not a verified
 * entitlement. The result is never itself permission to write game files.
 * Real operations keep their existing service-layer authorization checks.
 */
data class SteamCapabilities(
    val authenticated: Boolean,
    val entitlementVerified: Boolean,
    val online: Boolean,
    val cloudAvailable: Boolean
)

enum class SteamAccessResult {
    SIGN_IN_REQUIRED,
    ENTITLEMENT_UNVERIFIED,
    NETWORK_UNAVAILABLE,
    CLOUD_UNAVAILABLE,
    AVAILABLE_FOR_FURTHER_CHECKS
}

object SteamCapabilityGate {
    fun gameDownload(c: SteamCapabilities): SteamAccessResult = when {
        !c.authenticated -> SteamAccessResult.SIGN_IN_REQUIRED
        !c.entitlementVerified -> SteamAccessResult.ENTITLEMENT_UNVERIFIED
        !c.online -> SteamAccessResult.NETWORK_UNAVAILABLE
        else -> SteamAccessResult.AVAILABLE_FOR_FURTHER_CHECKS
    }

    fun cloudSaves(c: SteamCapabilities): SteamAccessResult = when {
        !c.authenticated -> SteamAccessResult.SIGN_IN_REQUIRED
        !c.online -> SteamAccessResult.NETWORK_UNAVAILABLE
        !c.cloudAvailable -> SteamAccessResult.CLOUD_UNAVAILABLE
        else -> SteamAccessResult.AVAILABLE_FOR_FURTHER_CHECKS
    }

    fun cloudSync(c: SteamCapabilities): SteamAccessResult = cloudSaves(c)
}
