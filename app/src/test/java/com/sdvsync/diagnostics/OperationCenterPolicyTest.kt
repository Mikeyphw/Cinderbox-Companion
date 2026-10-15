package com.sdvsync.diagnostics

import org.junit.Assert.*
import org.junit.Test

class OperationCenterPolicyTest {
    private fun items(game: String = "IDLE", mods: String = "IDLE", pending: Boolean = false,
        journals: Set<String> = emptySet(), outcomes: List<String> = emptyList()) =
        OperationCenterPolicy.build(game, mods, false, false, false, pending, journals, outcomes)

    @Test fun noPendingOperationsAreReadOnlyIdle() {
        val cards = items()
        assertEquals(listOf("game_download", "mod_download"), cards.map { it.id })
        assertTrue(cards.all { it.status == CenterStatus.IDLE })
    }
    @Test fun interruptedDownloadIsActionableWithoutImplicitResume() {
        val cards = items(game = "ERROR", journals = setOf("download"))
        assertEquals(CenterStatus.ACTION_REQUIRED, cards.first().status)
        assertTrue(cards.any { it.id == "download" && it.action == "Open Downloads" })
    }
    @Test fun pendingModApprovalHasExplicitReviewAction() {
        val cards = items(mods = "REVIEW_REQUIRED", pending = true)
        assertTrue(cards.any { it.id == "mod_review" && it.action == "Open Mods" })
        assertEquals(CenterStatus.ACTION_REQUIRED, cards[1].status)
    }
    @Test fun unknownJournalNamesDoNotAppearOrLeak() {
        assertFalse(items(journals = setOf("../../private", "secret")).any { it.id.contains("secret") })
    }
    @Test fun eachKnownJournalHasRecoveryGuidance() {
        val ids = setOf("download", "mod_install", "mod_profile", "mod_batch", "game_repair", "save_restore")
        val cards = items(journals = ids)
        assertEquals(ids, cards.drop(2).map { it.id }.toSet())
        assertTrue(cards.drop(2).all { it.status == CenterStatus.ACTION_REQUIRED && it.action.isNotBlank() })
    }
    @Test fun syncConflictAndStalePreviewNeedManualReview() {
        for (outcome in listOf("CONFLICT", "STALE_PREVIEW", "ERROR")) {
            val card = items(outcomes = listOf("SUCCESS", outcome)).last()
            assertEquals("sync", card.id)
            assertEquals(CenterStatus.ACTION_REQUIRED, card.status)
        }
    }
    @Test fun unknownSyncOutcomeIsIgnored() {
        assertFalse(items(outcomes = listOf("some/path/token")).any { it.id == "sync" })
    }
    @Test fun percentageIsClampedAndNanRejected() {
        assertNull(OperationCenterPolicy.percent(Float.NaN))
        assertEquals(100, OperationCenterPolicy.percent(2f))
        assertEquals(0, OperationCenterPolicy.percent(-2f))
    }
    @Test fun onlyActiveOperationsExposeProgress() {
        val cards = OperationCenterPolicy.build("COMPLETED", "DOWNLOADING", false, false,
            false, false, emptySet(), emptyList(), 80, 40)
        assertNull(cards.first().percent)
        assertEquals(40, cards[1].percent)
    }
}
