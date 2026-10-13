package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class VerifiedReleaseAssetTest {
    private val digest = "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

    private fun sample(url: String =
        "https://github.com/Ekyso/SMAPI-For-Cinderbox/releases/download/4.5.2.5/smapi-internal.zip",
        sha: String? = digest,
        size: Long = 3
    ) = GitHubReleaseInfo(
        tagName = "4.5.2.5", version = "4.5.2.5", assetUrl = url,
        assetSize = size, assetName = "smapi-internal.zip", publishedAt = "", assetDigest = sha
    )

    @Test fun acceptsOfficialSmapiReleaseDigest() {
        assertEquals(32, VerifiedReleaseAsset.expectedDigest(
            sample(), GitHubReleaseChecker.SMAPI_REPO
        ).size)
    }

    @Test fun rejectsOffDomainRelease() {
        try {
            VerifiedReleaseAsset.expectedDigest(
                sample(url = "https://evil.example/Ekyso/SMAPI-For-Cinderbox/releases/download/4.5.2.5/smapi-internal.zip"),
                GitHubReleaseChecker.SMAPI_REPO
            )
            fail("Off-domain release was trusted")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun rejectsMissingDigest() {
        try {
            VerifiedReleaseAsset.expectedDigest(sample(sha = null), GitHubReleaseChecker.SMAPI_REPO)
            fail("Digest-free release was trusted")
        } catch (_: IllegalArgumentException) { }
    }

    @Test fun cachedFileMustMatchSizeAndDigest() {
        val dir = Files.createTempDirectory("smapi-sha").toFile()
        try {
            val file = File(dir, "smapi-internal.zip")
            file.writeText("abc")
            VerifiedReleaseAsset.verifyCached(file, sample(), GitHubReleaseChecker.SMAPI_REPO)
            file.writeText("bad")
            try {
                VerifiedReleaseAsset.verifyCached(file, sample(), GitHubReleaseChecker.SMAPI_REPO)
                fail("Modified cache was accepted")
            } catch (_: IllegalArgumentException) { }
        } finally { dir.deleteRecursively() }
    }
}
