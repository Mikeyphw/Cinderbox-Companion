package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

class ModQueueControlPolicyTest {
    @Test fun activeAndQueuedCanPauseButInstallationCannot() {
        assertTrue(ModQueueControlPolicy.canPause("QUEUED"))
        assertTrue(ModQueueControlPolicy.canPause("DOWNLOADING"))
        for (status in listOf("VALIDATING", "INSTALLING", "REVIEW_REQUIRED", "INSTALLED")) {
            assertFalse(ModQueueControlPolicy.canPause(status))
            assertFalse(ModQueueControlPolicy.canCancel(status))
        }
    }

    @Test fun pausedNeedsAnExplicitSameSessionResume() {
        assertTrue(ModQueueControlPolicy.canResumeInSession("PAUSED"))
        for (status in listOf("INTERRUPTED", "FAILED", "DOWNLOADING", "INSTALLED")) {
            assertFalse(ModQueueControlPolicy.canResumeInSession(status))
        }
    }

    @Test fun reorderIsAdjacentAndBounded() {
        assertTrue(ModQueueControlPolicy.validMove(1, 3, -1))
        assertTrue(ModQueueControlPolicy.validMove(1, 3, 1))
        assertFalse(ModQueueControlPolicy.validMove(0, 3, -1))
        assertFalse(ModQueueControlPolicy.validMove(2, 3, 1))
        assertFalse(ModQueueControlPolicy.validMove(-1, 3, 1))
        assertFalse(ModQueueControlPolicy.validMove(1, 3, 0))
        assertFalse(ModQueueControlPolicy.validMove(1, 3, 999))
    }

    @Test fun freshLinkIsTiedToOriginalExactNexusIdentity() {
        assertTrue(ModQueueControlPolicy.freshLinkAllowed("nexus", "50535", "178239", "INTERRUPTED"))
        assertTrue(ModQueueControlPolicy.freshLinkAllowed("nexus", "50535", "178239", "PAUSED"))
        assertFalse(ModQueueControlPolicy.freshLinkAllowed("nexus", "50535", "178239", "INSTALLED"))
        assertFalse(ModQueueControlPolicy.freshLinkAllowed("nexus", "50535", "0", "FAILED"))
        assertFalse(ModQueueControlPolicy.freshLinkAllowed("nexus", "../1", "5", "FAILED"))
        assertFalse(ModQueueControlPolicy.freshLinkAllowed("local", "50535", "178239", "FAILED"))
    }
}
