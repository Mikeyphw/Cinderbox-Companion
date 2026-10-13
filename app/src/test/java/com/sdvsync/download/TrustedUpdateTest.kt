package com.sdvsync.download

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TrustedUpdateTest {
    private val url = "https://github.com/Mikeyphw/Cinderbox-Companion/releases/download/v2/CinderboxCompanion-v2.apk"
    private val name = "CinderboxCompanion-v2.apk"
    private val digest = "sha256:" + "a".repeat(64)

    @Test fun acceptsPinnedSourceAndDigest() {
        assertEquals("a".repeat(64), TrustedUpdate.expectedSha256(url, name, 1234, digest))
    }

    @Test fun rejectsUntrustedOrIncompleteReleases() {
        val variants = listOf(
            url.replace("https:", "http:") to digest,
            url.replace("Mikeyphw", "ObfuscatedVoid") to digest,
            url.replace("github.com", "github.com.evil.example") to digest,
            url to null
        )
        variants.forEach { (source, checksum) ->
            assertTrue(runCatching { TrustedUpdate.expectedSha256(source, name, 1234, checksum) }.isFailure)
        }
        assertTrue(runCatching { TrustedUpdate.expectedSha256(url, "../evil.apk", 100, digest) }.isFailure)
        assertTrue(runCatching { TrustedUpdate.expectedSha256(url, name, 0, digest) }.isFailure)
        assertTrue(runCatching { TrustedUpdate.expectedSha256(url, name, TrustedUpdate.MAX_APK_BYTES + 1, digest) }.isFailure)
    }

    @Test fun checksFinalDownloadHost() {
        assertTrue(TrustedUpdate.allowedFinalHost("release-assets.githubusercontent.com"))
        assertFalse(TrustedUpdate.allowedFinalHost("evil.example"))
    }

    @Test fun checksDigest() {
        val actual = java.security.MessageDigest.getInstance("SHA-256").digest("ok".toByteArray())
        assertTrue(TrustedUpdate.matchesSha256("ok".toByteArray(), TrustedUpdate.hex(actual)))
        assertFalse(TrustedUpdate.matchesSha256("not ok".toByteArray(), TrustedUpdate.hex(actual)))
    }
}
