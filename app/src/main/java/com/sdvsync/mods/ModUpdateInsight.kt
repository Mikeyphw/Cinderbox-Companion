package com.sdvsync.mods

import com.sdvsync.mods.models.ModUpdateInfo
import java.net.URI

/** A remote observation; UNKNOWN is not proof that a mod is current. */
data class ModUpdateObservation(
    val uniqueID: String,
    val installedVersion: String,
    val candidateVersion: String?,
    val status: UpdateAssessment
)

data class ModUpdateCheckResult(
    val updates: Map<String, ModUpdateInfo>,
    val observations: Map<String, ModUpdateObservation>,
    val checkedAtMs: Long
)

/** Pure rendering policy and data checks. No network, filesystem, or installer calls. */
object ModUpdateInsight {
    const val STALE_AFTER_MS: Long = 4 * 60 * 60 * 1000L
    const val MAX_CHANGELOG_INPUT = 16384
    const val MAX_CHANGELOG_DISPLAY = 4000

    fun observationFor(
        id: String,
        version: String,
        observations: Map<String, ModUpdateObservation>
    ): ModUpdateObservation? = observations[ModUpdatePolicy.normalizedId(id)]
        ?.takeIf { it.installedVersion == version }

    fun freshness(checkedAtMs: Long, nowMs: Long): String = when {
        checkedAtMs <= 0L -> "Never checked"
        checkedAtMs > nowMs -> "Check time is invalid — refresh required"
        nowMs - checkedAtMs > STALE_AFTER_MS -> "Previous check expired — refresh required"
        else -> "Checked ${((nowMs - checkedAtMs) / 60000L)} minutes ago"
    }

    fun label(status: UpdateAssessment): String = when (status) {
        UpdateAssessment.NEWER -> "Update available"
        UpdateAssessment.CURRENT -> "Current version"
        UpdateAssessment.INSTALLED_AHEAD -> "Installed version ahead"
        UpdateAssessment.UNCOMPARABLE -> "Versions cannot be compared"
        UpdateAssessment.UNKNOWN -> "Update status unknown"
    }

    /** Only explicit HTTPS provider URLs; never javascript:, file:, local or embedded credentials. */
    fun safeUpdateUrl(value: String?): String? = runCatching {
        if (value == null || value.length !in 12..2048 || value.any(Char::isISOControl)) return@runCatching null
        val uri = URI(value)
        val host = uri.host?.lowercase(java.util.Locale.ROOT) ?: return@runCatching null
        if (uri.scheme?.lowercase(java.util.Locale.ROOT) != "https" || uri.rawUserInfo != null ||
            uri.port != -1 || host !in setOf("smapi.io", "www.nexusmods.com", "nexusmods.com",
                "github.com", "www.github.com")) return@runCatching null
        value
    }.getOrNull()

    /** Untrusted Nexus markup becomes inert, capped text; no HTML parser/WebView or active links. */
    fun plainChangelog(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        val clipped = raw.take(MAX_CHANGELOG_INPUT)
        val unsafeBlocks = Regex("(?is)<(script|style|iframe|object|svg|form)\\b[^>]*>.*?</\\1\\s*>")
        val noBlocks = clipped.replace(unsafeBlocks, " ")
        val noTags = noBlocks.replace(Regex("(?s)<[^>]*>"), " ")
        val decoded = noTags.replace("&amp;", "&", ignoreCase = true)
            .replace("&lt;", "<", ignoreCase = true)
            .replace("&gt;", ">", ignoreCase = true)
            .replace("&quot;", "\"", ignoreCase = true)
            .replace("&#39;", "'", ignoreCase = true)
            .replace("&nbsp;", " ", ignoreCase = true)
        val plain = decoded.replace(Regex("[\\p{Cc}&&[^\\n\\t]]"), " ")
            .replace(Regex("[ \\t]{2,}"), " ")
            .trim().take(MAX_CHANGELOG_DISPLAY)
        return plain.takeIf { it.isNotBlank() }
    }
}
