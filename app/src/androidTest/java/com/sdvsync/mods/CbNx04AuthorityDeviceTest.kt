package com.sdvsync.mods

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** Synthetic cache-only fixtures; never reads, renames or repairs actual Mods/. */
@RunWith(AndroidJUnit4::class)
class CbNx04AuthorityDeviceTest {
    private fun fixture(block: (File) -> Unit) {
        val root = File(InstrumentationRegistry.getInstrumentation().targetContext.cacheDir,
            "cbnx04-" + UUID.randomUUID()).apply { mkdirs() }
        try { block(root) } finally { root.deleteRecursively() }
    }
    private fun manifest(root: File, dir: String, nexus: String) {
        val folder = File(root, dir).apply { mkdirs() }
        File(folder, "manifest.json").writeText(JSONObject()
            .put("Name", "Fixture").put("UniqueID", "test.$dir")
            .put("Version", "1.2.0")
            .put("UpdateKeys", JSONArray().put("Nexus:$nexus")).toString())
    }
    private fun job(status: String = "INSTALLED") = ModDownloadRecord(
        id = UUID.randomUUID().toString(), name = "Test", source = "nexus",
        modId = "50535", fileId = "178239", status = status,
        received = 123L, total = 123L, createdAt = 1L,
        updatedAt = 2L, detail = "synthetic")
    private fun item(snapshot: JSONObject) = snapshot.getJSONArray("items").getJSONObject(0)
    private fun reviews(root: File) = File(root, "private-review").apply { mkdirs() }
    private fun archive(root: File): File = File(root, "synthetic-source.zip").apply {
        java.util.zip.ZipOutputStream(outputStream()).use { zip ->
            zip.putNextEntry(java.util.zip.ZipEntry("manifest.json"))
            zip.write("{\"Name\":\"Synthetic\"}".toByteArray())
            zip.closeEntry()
        }
    }

    @Test fun absentInventoryDoesNotClaimMissingMods() = fixture { root ->
        val scan = NexusPairingAuthority.snapshot(listOf(job()), File(root, "absent"), 10L, reviews(root))
        assertEquals("UNAVAILABLE", scan.getString("inventory_state"))
        assertEquals("UNKNOWN", item(scan).getString("installed_mod_state"))
        assertEquals("UNKNOWN", item(scan).getString("exact_file_installed"))
    }
    @Test fun verifiedManifestLinksModButNeverClaimsExactFile() = fixture { root ->
        manifest(root, "Enabled", "50535")
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 10L, reviews(root))
        assertEquals("QUALIFIED", scan.getString("inventory_state"))
        assertEquals("PRESENT", item(scan).getString("installed_mod_state"))
        assertEquals("1.2.0", item(scan).getString("installed_version"))
        assertEquals("UNKNOWN", item(scan).getString("exact_file_installed"))
        assertFalse(item(scan).getBoolean("archive_checksum_qualified"))
        assertEquals("NO_RETAINED_ARCHIVE", item(scan).getString("archive_proof_state"))
    }
    @Test fun queuedHandoffNeverMarksArchiveAsDownloaded() = fixture { root ->
        manifest(root, "Enabled", "50535")
        val scan = NexusPairingAuthority.snapshot(listOf(job("QUEUED")), root, 10L, reviews(root))
        assertFalse(item(scan).getBoolean("journal_transfer_reported"))
        assertEquals("UNKNOWN", item(scan).getString("update_state"))
        assertEquals("NOT_PERFORMED", scan.getString("remote_update_check"))
    }
    @Test fun validationReportIsNotArchiveChecksumProof() = fixture { root ->
        val scan = NexusPairingAuthority.snapshot(listOf(job("VALIDATING")), root, 10L, reviews(root))
        assertTrue(item(scan).getBoolean("journal_transfer_reported"))
        assertFalse(item(scan).getBoolean("archive_checksum_qualified"))
        assertEquals("NO_RETAINED_ARCHIVE", item(scan).getString("archive_proof_state"))
        assertEquals("NOT_LINKED", item(scan).getString("installed_mod_state"))
        assertEquals("NO_RETAINED_ARCHIVE", item(scan).getString("archive_proof_state"))
    }
    @Test fun duplicateProviderKeysCannotConfirmInstalledIdentity() = fixture { root ->
        manifest(root, "One", "50535"); manifest(root, "Two", "50535")
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 10L, reviews(root))
        assertEquals("AMBIGUOUS", item(scan).getString("installed_mod_state"))
        assertFalse(item(scan).has("installed_version"))
    }
    @Test fun malformedManifestFailsClosedWithoutPathsOrSecrets() = fixture { root ->
        File(root, "Malformed").mkdirs()
        File(root, "Malformed/manifest.json").writeText("{invalid-json")
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 10L, reviews(root))
        assertEquals("UNAVAILABLE", scan.getString("inventory_state"))
        assertFalse(scan.toString().contains(root.absolutePath))
        assertFalse(scan.toString().contains("invalid-json"))
    }
    @Test fun disabledManifestCannotBeMistakenForEnabled() = fixture { root ->
        manifest(root, ".Disabled", "50535")
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 10L, reviews(root))
        assertEquals("DISABLED_PRESENT", item(scan).getString("installed_mod_state"))
        assertEquals("UNKNOWN", item(scan).getString("update_state"))
        assertTrue(File(root, ".Disabled").isDirectory)
    }

    @Test fun privateArchiveDigestAndExactJobMatchOnlyAtScanTime() = fixture { root ->
        val receipts = reviews(root)
        val record = job("REVIEW_REQUIRED")
        ModReviewQueue(receipts).enqueue(archive(root), "Synthetic", "nexus",
            record.modId, record.fileId, record.id)
        val scan = NexusPairingAuthority.snapshot(listOf(record), root, 10L, receipts)
        val row = item(scan)
        assertTrue(row.getBoolean("archive_checksum_qualified"))
        assertEquals("VERIFIED_AT_SCAN", row.getString("archive_proof_state"))
        assertEquals("LOCAL_ZIP_VS_APP_RECEIPT", row.getString("archive_proof_scope"))
        assertEquals("UNKNOWN", row.getString("exact_file_installed"))
        assertEquals("UNKNOWN", row.getString("update_state"))
    }

    @Test fun tamperedRetainedArchiveNeverQualifiesDigest() = fixture { root ->
        val receipts = reviews(root)
        val record = job("REVIEW_REQUIRED")
        ModReviewQueue(receipts).enqueue(archive(root), "Synthetic", "nexus",
            record.modId, record.fileId, record.id)
        File(receipts, "mod-review-pending.zip").appendBytes(byteArrayOf(42))
        val row = item(NexusPairingAuthority.snapshot(listOf(record), root, 10L, receipts))
        assertFalse(row.getBoolean("archive_checksum_qualified"))
        assertEquals("UNAVAILABLE", row.getString("archive_proof_state"))
    }

    @Test fun wrongExactFileReceiptCannotProveAnotherJob() = fixture { root ->
        val receipts = reviews(root)
        val record = job("REVIEW_REQUIRED")
        ModReviewQueue(receipts).enqueue(archive(root), "Synthetic", "nexus",
            record.modId, "190561", record.id)
        val row = item(NexusPairingAuthority.snapshot(listOf(record), root, 10L, receipts))
        assertFalse(row.getBoolean("archive_checksum_qualified"))
        assertEquals("UNAVAILABLE", row.getString("archive_proof_state"))
    }

    private fun smapi(checkedAt: Long, version: String = "1.2.0",
                      candidate: String? = "1.3.0",
                      assessment: UpdateAssessment = UpdateAssessment.NEWER) =
        NexusUpdateEvidence.Snapshot(checkedAt, mapOf("test.enabled" to
            ModUpdateObservation("test.Enabled", version, candidate, assessment)))

    @Test fun freshAppOwnedSmapiCandidateMayReportNewerModNotExactFile() = fixture { root ->
        manifest(root, "Enabled", "50535")
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), smapi(999_000L))
        assertEquals("SMAPI_CACHE_FRESH", scan.getString("remote_update_check"))
        assertEquals("NEWER", item(scan).getString("update_state"))
        assertEquals("1.3.0", item(scan).getString("candidate_version"))
        assertEquals("CACHED_SMAPI_MOD_VERSION", item(scan).getString("update_proof_scope"))
        assertEquals("UNKNOWN", item(scan).getString("exact_file_installed"))
        assertFalse(item(scan).getBoolean("archive_checksum_qualified"))
    }

    @Test fun expiredOrClockInvalidSmapiCacheCannotShowAnUpdate() = fixture { root ->
        manifest(root, "Enabled", "50535")
        // The previous fixture used 15_000_000 - 999_000 = 14_001_000 ms,
        // which is LESS than four hours and therefore wrongly expected STALE.
        // Test the exact inclusive boundary and the first expired millisecond.
        val checkedAt = 999_000L
        val fourHours = 4L * 60L * 60L * 1000L
        assertEquals(14_400_000L, fourHours)
        assertEquals(fourHours, NexusUpdateEvidence.FRESH_MS)
        val atBoundary = NexusPairingAuthority.snapshot(listOf(job()), root,
            checkedAt + fourHours, reviews(root), smapi(checkedAt))
        assertEquals("SMAPI_CACHE_FRESH", atBoundary.getString("remote_update_check"))
        assertEquals("NEWER", item(atBoundary).getString("update_state"))
        assertEquals("1.3.0", item(atBoundary).getString("candidate_version"))
        val expired = NexusPairingAuthority.snapshot(listOf(job()), root,
            checkedAt + fourHours + 1L, reviews(root), smapi(checkedAt))
        assertEquals("SMAPI_CACHE_STALE", expired.getString("remote_update_check"))
        assertEquals("UNKNOWN", item(expired).getString("update_state"))
        assertFalse(item(expired).has("candidate_version"))
        val clock = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), smapi(1_000_001L))
        assertEquals("CLOCK_INVALID", clock.getString("remote_update_check"))
        assertEquals("UNKNOWN", item(clock).getString("update_state"))
        assertFalse(item(clock).has("candidate_version"))
    }

    @Test fun versionOrIdentifierMismatchCannotPromoteCachedCandidate() = fixture { root ->
        manifest(root, "Enabled", "50535")
        val badVersion = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), smapi(999_000L, version = "1.2.1"))
        assertEquals("UNKNOWN", item(badVersion).getString("update_state"))
        val wrongId = NexusUpdateEvidence.Snapshot(999_000L, mapOf("other.mod" to
            ModUpdateObservation("other.mod", "1.2.0", "1.3.0", UpdateAssessment.NEWER)))
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), wrongId)
        assertEquals("UNKNOWN", item(scan).getString("update_state"))
    }

    @Test fun disabledOrAmbiguousSmapiLinkNeverProducesUpdateBadge() = fixture { root ->
        manifest(root, ".Disabled", "50535")
        var scan = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), NexusUpdateEvidence.Snapshot(999_000L, mapOf("test..disabled" to
                ModUpdateObservation("test..Disabled", "1.2.0", "1.3.0", UpdateAssessment.NEWER))))
        assertEquals("UNKNOWN", item(scan).getString("update_state"))
        manifest(root, "Enabled", "50535")
        scan = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), smapi(999_000L))
        assertEquals("AMBIGUOUS", item(scan).getString("installed_mod_state"))
        assertEquals("UNKNOWN", item(scan).getString("update_state"))
    }

    @Test fun forgedOrMalformedVersionCannotBeExportedAsUpdateProof() = fixture { root ->
        manifest(root, "Enabled", "50535")
        val forged = smapi(999_000L, candidate = "1.1.0", assessment = UpdateAssessment.NEWER)
        val bad = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), forged)
        assertEquals("UNKNOWN", item(bad).getString("update_state"))
        val injected = smapi(999_000L, candidate = "nxm://secret", assessment = UpdateAssessment.NEWER)
        val scan = NexusPairingAuthority.snapshot(listOf(job()), root, 1_000_000L,
            reviews(root), injected)
        assertEquals("UNKNOWN", item(scan).getString("update_state"))
        assertFalse(scan.toString().contains("nxm://"))
    }
    private fun dashboardFixture(enabled: Boolean = true, id: String = "test.Enabled") =
        com.sdvsync.mods.models.InstalledMod(
            com.sdvsync.mods.models.ModManifest("Synthetic", "Test", "1.2.0", id,
                "Synthetic", updateKeys = listOf("Nexus:50535")),
            "Enabled", "synthetic", enabled)

    private fun dashboardObservations() = mapOf("test.enabled" to
        ModUpdateObservation("test.Enabled", "1.2.0", "1.3.0", UpdateAssessment.NEWER))

    @Test fun dashboardFreshSmapiEvidenceIsModOnlyNotExactFile() {
        val result = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture()),
            dashboardObservations(), emptyMap(), 9_999_000L, 10_000_000L)
        assertEquals("SMAPI_CACHE_FRESH", result.freshness)
        assertEquals(1, result.availableCount)
        assertEquals("NEWER", result.entries.single().status)
        assertEquals("50535", result.entries.single().nexusModId)
    }

    @Test fun dashboardFourHourBoundaryAndClockAnomalyAreUncertain() {
        val now = 30_000_000L
        val valid = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture()),
            dashboardObservations(), emptyMap(), now - NexusUpdateEvidence.FRESH_MS, now)
        assertEquals(1, valid.availableCount)
        val stale = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture()),
            dashboardObservations(), emptyMap(), now - NexusUpdateEvidence.FRESH_MS - 1L, now)
        assertEquals("SMAPI_CACHE_STALE", stale.freshness)
        assertEquals(0, stale.availableCount)
        assertEquals("UNKNOWN", stale.entries.single().status)
        val future = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture()),
            dashboardObservations(), emptyMap(), now + 1L, now)
        assertEquals("CLOCK_INVALID", future.freshness)
        assertEquals(0, future.availableCount)
    }

    @Test fun dashboardDisabledDuplicateAndIgnoredVersionsAreNotActionable() {
        val now = 10_000_000L
        val ignored = mapOf("test.enabled" to com.sdvsync.mods.models.ModUpdateInfo(
            "test.Enabled", "1.2.0", "1.3.0", null, "Nexus:50535"))
        val view = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture()),
            dashboardObservations(), ignored, now - 1000L, now)
        assertEquals(0, view.availableCount)
        assertEquals(1, view.ignoredCount)
        val duplicate = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture(),
            dashboardFixture(id = "TEST.ENABLED")), dashboardObservations(),
            emptyMap(), now - 1000L, now)
        assertEquals(0, duplicate.availableCount)
        assertTrue(duplicate.entries.all { it.status == "AMBIGUOUS" })
        val disabled = ModUpdatesDashboardPolicy.evaluate(listOf(dashboardFixture(false)),
            dashboardObservations(), emptyMap(), now - 1000L, now)
        assertEquals("DISABLED", disabled.entries.single().status)
    }

}
