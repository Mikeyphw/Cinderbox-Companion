package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

/** Pure security/rendering tests. No device files, HTTP, browser, or provider credentials. */
class ModDownloadEvidencePolicyTest {
    private fun observed() = ModDownloadEvidencePolicy.Observation(
        jobId = "fixture-job", modId = "50535", fileId = "178239", archiveState = "VERIFIED_AT_SCAN",
        archiveQualified = true, archiveScope = "LOCAL_ZIP_VS_APP_RECEIPT",
        inventoryState = "QUALIFIED", modState = "PRESENT", exactFileInstalled = "UNKNOWN")
    private fun evidence(value: ModDownloadEvidencePolicy.Observation? = observed()) =
        ModDownloadEvidencePolicy.evaluate("fixture-job", "nexus", "50535", "178239", "REVIEW_REQUIRED", value)

    @Test fun localArchiveProofNeverPromotesExactInstalledFile() {
        val result = evidence()
        assertTrue(result.verifiedAtScan)
        assertTrue(result.archive.contains("app-owned receipt"))
        assertTrue(result.mod.contains("mod-level only"))
        assertTrue(result.exactFile.contains("not verified"))
    }
    @Test fun anotherJobCannotBorrowPrivateArchiveProof() {
        val result = evidence(observed().copy(jobId = "different-job"))
        assertFalse(result.verifiedAtScan)
    }
    @Test fun differentExactFileCannotBorrowReceiptProof() {
        val result = evidence(observed().copy(fileId = "190561"))
        assertFalse(result.verifiedAtScan)
        assertTrue(result.archive.contains("unavailable"))
    }
    @Test fun missingOrCorruptProofNeverMeansDownloaded() {
        val none = evidence(observed().copy(archiveQualified = false, archiveState = "NO_RETAINED_ARCHIVE"))
        assertFalse(none.verifiedAtScan)
        assertTrue(none.archive.contains("download history is separate"))
        val corrupt = evidence(observed().copy(archiveQualified = true, archiveState = "UNAVAILABLE"))
        assertFalse(corrupt.verifiedAtScan)
    }
    @Test fun wrongScopeAndForgedExactFileClaimFailClosed() {
        assertFalse(evidence(observed().copy(archiveScope = "NEXUS_SIGNED")).verifiedAtScan)
        val forged = evidence(observed().copy(exactFileInstalled = "CONFIRMED"))
        assertFalse(forged.verifiedAtScan)
        assertTrue(forged.mod.contains("unknown"))
    }
    @Test fun unavailableInventoryCannotClaimInstalled() {
        val result = evidence(observed().copy(inventoryState = "UNAVAILABLE"))
        assertTrue(result.mod.contains("unknown"))
        assertTrue(result.exactFile.contains("not verified"))
    }
    @Test fun disabledAndAmbiguousModEvidenceRemainDistinct() {
        assertTrue(evidence(observed().copy(modState = "DISABLED_PRESENT")).mod.contains("disabled"))
        assertTrue(evidence(observed().copy(modState = "AMBIGUOUS")).mod.contains("not verified"))
    }
    @Test fun invalidIdentityAndUnknownStateRefuseEvidence() {
        assertFalse(ModDownloadEvidencePolicy.evaluate("fixture-job", "local", "50535", "178239", "INSTALLED", observed()).verifiedAtScan)
        assertFalse(ModDownloadEvidencePolicy.evaluate("fixture-job", "nexus", "50535", "1/2", "REVIEW_REQUIRED", observed()).verifiedAtScan)
        assertFalse(ModDownloadEvidencePolicy.evaluate("fixture-job", "nexus", "50535", "178239", "FORGED", observed()).verifiedAtScan)
    }
}
