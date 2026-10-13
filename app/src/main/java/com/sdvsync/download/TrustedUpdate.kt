package com.sdvsync.download

import java.net.URI
import java.security.MessageDigest
import java.util.Locale

/** Fail-closed policy for APKs supplied by the fork's GitHub release feed. */
object TrustedUpdate {
    private const val REPO_PATH = "/Mikeyphw/Cinderbox-Companion/releases/download/"
    const val MAX_APK_BYTES: Long = 200L * 1024 * 1024
    private val digestPattern = Regex("sha256:([0-9a-fA-F]{64})")
    private val filenamePattern = Regex("CinderboxCompanion-[A-Za-z0-9._-]+\\.apk")

    fun expectedSha256(assetUrl: String, assetName: String, assetSize: Long, digest: String?): String {
        require(filenamePattern.matches(assetName)) { "Unexpected update APK name" }
        require(assetSize in 1..MAX_APK_BYTES) { "Update APK size is missing or exceeds limit" }
        val uri = URI(assetUrl)
        require(
            uri.scheme == "https" && uri.host == "github.com" && uri.port == -1 &&
                uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null &&
                uri.rawPath.startsWith(REPO_PATH) &&
                uri.rawPath.endsWith("/$assetName")
        ) { "Update source is not an allowed GitHub release URL" }
        return requireNotNull(digestPattern.matchEntire(digest ?: "")) {
            "Update release has no valid SHA-256 digest"
        }.groupValues[1].lowercase(Locale.ROOT)
    }

    fun allowedFinalHost(host: String): Boolean =
        host == "github.com" || host == "release-assets.githubusercontent.com"

    fun hex(bytes: ByteArray): String = bytes.joinToString("") {
        "%02x".format(Locale.ROOT, it.toInt() and 0xff)
    }

    fun matchesSha256(data: ByteArray, digest: String): Boolean =
        MessageDigest.isEqual(
            MessageDigest.getInstance("SHA-256").digest(data),
            digest.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        )
}
