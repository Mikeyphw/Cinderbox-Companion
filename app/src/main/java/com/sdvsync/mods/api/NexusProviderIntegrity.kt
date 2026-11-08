package com.sdvsync.mods.api

import java.util.Locale

/**
 * Provider-supplied read-only metadata integrity. This validates values from Nexus
 * response payloads, NOT that a mod is safe, available, downloadable or installed.
 * The caller must preserve API errors instead of inventing a successful empty page.
 */
internal object NexusProviderIntegrity {
    private val positiveDecimal = Regex("[1-9][0-9]{0,9}")

    /** Never turn missing/null/fractional/negative IDs into a navigable mod or file 0. */
    fun positiveId(value: Any?): String? {
        val raw = when (value) {
            is Int -> value.toString()
            is Long -> value.toString()
            is String -> value.trim()
            else -> return null
        }
        if (!positiveDecimal.matches(raw)) return null
        return raw.toIntOrNull()?.takeIf { it > 0 }?.toString()
    }

    /** GraphQL totalCount must be a genuine JSON integer, not null/string/default zero. */
    fun totalCount(value: Any?): Int? = when (value) {
        is Int -> value.takeIf { it >= 0 }
        is Long -> value.takeIf { it in 0..Int.MAX_VALUE.toLong() }?.toInt()
        else -> null
    }

    /** Page progress is measured in raw provider nodes, not deduplicated visible cards. */
    fun hasMore(offset: Int, rawNodeCount: Int, totalCount: Int): Boolean {
        require(offset >= 0 && rawNodeCount in 0..NEXUS_SEARCH_PAGE_SIZE && totalCount >= 0)
        return offset.toLong() + rawNodeCount.toLong() < totalCount.toLong()
    }

    /** Missing category is unknown; only an explicitly primary file can infer Main. */
    fun fileCategory(raw: String?, explicitlyPrimary: Boolean): String {
        val cleaned = raw?.trim()?.take(80).orEmpty()
        if (cleaned.isEmpty() || cleaned.equals("null", ignoreCase = true)) {
            return if (explicitlyPrimary) "MAIN" else "UNSPECIFIED"
        }
        return cleaned.uppercase(Locale.ROOT)
    }

    /** Modern calendar range and overflow guard, normalized to milliseconds for UI. */
    fun epochSecondsToMillis(seconds: Long): Long =
        if (seconds in 946684800L..4102444799L) seconds * 1000L else 0L
}
