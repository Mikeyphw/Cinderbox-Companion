package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class M24DepotManifestIdentityTest {
    @Test fun canonicalFingerprintIndependentOfDepotIterationOrder() {
        val a = M24DepotManifestIdentity.snapshot("public", 123L, linkedMapOf(222 to "987", 111 to "456"))
        val b = M24DepotManifestIdentity.snapshot("public", 123L, linkedMapOf(111 to "456", 222 to "987"))
        assertEquals(a, b)
        assertEquals(64, a.fingerprint.length)
    }
    @Test fun branchBuildOrDepotDriftChangesIdentity() {
        val a = M24DepotManifestIdentity.snapshot("public", 7L, mapOf(111 to "555"))
        val others = listOf(
            M24DepotManifestIdentity.snapshot("beta", 7L, mapOf(111 to "555")),
            M24DepotManifestIdentity.snapshot("public", 8L, mapOf(111 to "555")),
            M24DepotManifestIdentity.snapshot("public", 7L, mapOf(111 to "556")))
        for (other in others) {
            assertNotEquals(a.fingerprint, other.fingerprint)
            try { M24DepotManifestIdentity.requireMatching(a.fingerprint, other); fail("Expected drift rejection") }
            catch (_: IllegalStateException) { }
        }
    }
    @Test fun missingOrMalformedManifestNeverAuthorizesNewTransfer() {
        for (bad in listOf(emptyMap(), mapOf(111 to "0"), mapOf(111 to "-1"), mapOf(0 to "5"))) {
            try { M24DepotManifestIdentity.snapshot("public", 7L, bad); fail("Expected invalid data") }
            catch (_: IllegalArgumentException) { }
        }
    }
    @Test fun journalBindingSurvivesRecreationAndNeverModifiesPartialPayload() {
        val root = Files.createTempDirectory("m24-pics-").toFile()
        try {
            val privateRoot = File(root, "owner").apply { mkdir() }
            val target = File(root, "target")
            val recovery = GameDownloadRecovery(privateRoot)
            recovery.beginStaged(target, "public", "windows", true)
            recovery.bindSteamBuildId(72)
            val fingerprint = M24DepotManifestIdentity.snapshot("public", 72, mapOf(300 to "222")).fingerprint
            recovery.bindDepotManifestFingerprint(fingerprint)
            val stage = recovery.requireActiveStage(target)
            File(stage, "partial.dat").writeText("keep")
            val cold = GameDownloadRecovery(privateRoot)
            assertEquals(fingerprint, cold.pending()!!.depotManifestFingerprint)
            cold.requireDepotManifestFingerprint(fingerprint)
            try { cold.bindDepotManifestFingerprint("0".repeat(64)); fail("Expected drift rejection") }
            catch (_: IllegalStateException) { }
            assertEquals("keep", File(stage, "partial.dat").readText())
            assertFalse(target.exists())
        } finally { root.deleteRecursively() }
    }
}
