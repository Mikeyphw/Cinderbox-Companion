package com.sdvsync.download

import org.junit.Assert.*
import org.junit.Test

class M24SteamSelectionPolicyTest {
    @Test fun rejectedWithoutLiveLogin() {
        assertEquals(M24SteamSelectionPolicy.Verdict.SIGNED_OUT,
            M24SteamSelectionPolicy.assess(false, 7, 7))
        assertThrows(IllegalStateException::class.java) {
            M24SteamSelectionPolicy.requireBound(false, 7, 7)
        }
    }
    @Test fun rejectedWithoutPicsBuildEvidence() {
        assertEquals(M24SteamSelectionPolicy.Verdict.BUILD_UNKNOWN,
            M24SteamSelectionPolicy.assess(true, 0, 0))
        assertEquals(M24SteamSelectionPolicy.Verdict.BUILD_UNKNOWN,
            M24SteamSelectionPolicy.assess(true, 7, null))
    }
    @Test fun rejectedOnBranchDrift() {
        assertEquals(M24SteamSelectionPolicy.Verdict.BRANCH_CHANGED,
            M24SteamSelectionPolicy.assess(true, 7, 8))
        assertThrows(IllegalStateException::class.java) {
            M24SteamSelectionPolicy.requireBound(true, 7, 8)
        }
    }
    @Test fun matchingPicsIsNotSteamLicenseOrManifestProof() {
        assertEquals(413150, M24SteamSelectionPolicy.APP_ID)
        assertEquals(M24SteamSelectionPolicy.Verdict.PICS_BOUND_ONLY,
            M24SteamSelectionPolicy.assess(true, 7, 7))
        M24SteamSelectionPolicy.requireBound(true, 7, 7)
    }
}
