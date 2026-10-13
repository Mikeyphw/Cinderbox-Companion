package com.sdvsync.download

import java.io.File
import java.net.URI
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.Locale
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.ensureActive
import okhttp3.OkHttpClient
import okhttp3.Request

/** GitHub API asset metadata is a transport integrity assertion, not publisher-signature proof. */
object VerifiedReleaseAsset {
    const val MAX_APK_BYTES = 250L * 1024 * 1024
    const val MAX_SMAPI_BYTES = 80L * 1024 * 1024
    private val digestPattern = Regex("sha256:([0-9a-fA-F]{64})")

    fun expectedDigest(release: GitHubReleaseInfo, repo: String): ByteArray {
        val isSmapi = repo == GitHubReleaseChecker.SMAPI_REPO
        require(isSmapi || repo == GitHubReleaseChecker.CINDERBOX_REPO) {
            "Unsupported release publisher"
        }
        val max = if (isSmapi) MAX_SMAPI_BYTES else MAX_APK_BYTES
        require(release.assetSize in 1..max) { "Release asset has invalid size" }
        val filename = release.assetName
        require(filename.matches(Regex("[A-Za-z0-9._-]+")) &&
            (if (isSmapi) filename.matches(GitHubReleaseChecker.SMAPI_ASSET_PATTERN)
                else filename.matches(GitHubReleaseChecker.CINDERBOX_ASSET_PATTERN))) {
            "Unexpected release filename"
        }
        val url = URI(release.assetUrl)
        val expectedPrefix = "/$repo/releases/download/".lowercase(Locale.ROOT)
        require(url.scheme == "https" && url.host == "github.com" && url.port == -1 &&
            url.rawUserInfo == null && url.rawQuery == null && url.rawFragment == null &&
            url.rawPath.lowercase(Locale.ROOT).startsWith(expectedPrefix) &&
            url.rawPath.endsWith("/$filename")) {
            "Release URL is not from the expected GitHub repository"
        }
        val digest = requireNotNull(digestPattern.matchEntire(release.assetDigest ?: "")) {
            "GitHub release is missing a SHA-256 asset digest"
        }.groupValues[1]
        return digest.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    }

    private fun checkFinalUrl(uri: URI) {
        require(uri.scheme == "https" && uri.rawUserInfo == null &&
            uri.host in setOf("github.com", "release-assets.githubusercontent.com") &&
            uri.port == -1) { "Untrusted GitHub download redirect" }
    }

    fun verifyCached(file: File, release: GitHubReleaseInfo, repo: String) {
        val expected = expectedDigest(release, repo)
        require(file.isFile && file.length() == release.assetSize) { "Cached release has wrong size" }
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val n = input.read(buffer)
                if (n < 0) break
                digest.update(buffer, 0, n)
            }
        }
        require(MessageDigest.isEqual(expected, digest.digest())) { "Cached release checksum mismatch" }
    }

    suspend fun download(
        client: OkHttpClient,
        release: GitHubReleaseInfo,
        repo: String,
        destination: File,
        progress: (Long, Long) -> Unit = { _, _ -> }
    ): File {
        val expected = expectedDigest(release, repo)
        val part = File(destination.parentFile, ".${destination.name}.download-part")
        check(!Files.isSymbolicLink(part.toPath()) && !Files.isSymbolicLink(destination.toPath())) {
            "Refusing symlinked release cache"
        }
        if (part.exists()) check(part.delete()) { "Stale download staging file cannot be removed" }
        try {
            // Disable implicit OkHttp redirects so every hop is HTTPS/allowlisted.
            val strictClient = client.newBuilder().followRedirects(false).followSslRedirects(false).build()
            var next = URI(release.assetUrl)
            var finalResponse: okhttp3.Response? = null
            for (hop in 0..5) {
                checkFinalUrl(next)
                val response = strictClient.newCall(Request.Builder().url(next.toString()).get().build())
                    .execute()
                if (response.code in 300..399) {
                    val location = response.header("Location")
                    response.close()
                    next = next.resolve(requireNotNull(location) { "Release redirect has no location" })
                } else {
                    finalResponse = response
                    break
                }
            }
            val responseToRead = checkNotNull(finalResponse) { "Too many GitHub release redirects" }
            responseToRead.use { response ->
                require(response.isSuccessful) { "HTTP ${response.code} fetching release" }
                checkFinalUrl(URI(response.request.url.toString()))
                val body = checkNotNull(response.body) { "Empty release response" }
                val declared = body.contentLength()
                require(declared == -1L || declared == release.assetSize) {
                    "HTTP length differs from release metadata"
                }
                val digest = MessageDigest.getInstance("SHA-256")
                var received = 0L
                part.outputStream().buffered().use { output ->
                    body.byteStream().use { input ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            coroutineContext.ensureActive()
                            val n = input.read(buffer)
                            if (n == -1) break
                            received += n
                            require(received <= release.assetSize) { "Release exceeds declared size" }
                            digest.update(buffer, 0, n)
                            output.write(buffer, 0, n)
                            progress(received, release.assetSize)
                        }
                    }
                }
                require(received == release.assetSize) { "Incomplete release download" }
                require(MessageDigest.isEqual(expected, digest.digest())) { "Release checksum mismatch" }
            }
            coroutineContext.ensureActive()
            // Both paths are inside the same app cache; do not expose partial downloads.
            Files.move(part.toPath(), destination.toPath(),
                StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
            return destination
        } finally {
            if (part.exists()) part.delete()
        }
    }
}
