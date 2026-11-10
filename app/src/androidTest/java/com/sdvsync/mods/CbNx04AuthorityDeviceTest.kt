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
}
