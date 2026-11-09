package com.sdvsync.mods.api

import java.net.URI
import java.net.URLDecoder
import java.nio.charset.StandardCharsets
import java.util.Locale

/** Strictly validates externally supplied NXM links before any API or filesystem operation. */
object NxmUriPolicy {
    data class Request(val modId: String, val fileId: String, val key: String, val expires: String)

    private val pathPattern = Regex("/mods/([1-9][0-9]{0,11})/files/([1-9][0-9]{0,11})")
    private val keyPattern = Regex("[A-Za-z0-9._~+/=-]{1,512}")
    private const val MAX_FUTURE_SECONDS = 7L * 24L * 3600L

    fun parse(raw: String?, nowEpochSeconds: Long = System.currentTimeMillis() / 1000L): Request? {
        if (raw.isNullOrEmpty() || raw.length > 2048 || raw.any { it.code < 32 }) return null
        return try {
            val uri = URI(raw)
            if (!uri.scheme.equals("nxm", ignoreCase = true) ||
                uri.host?.lowercase(Locale.ROOT) != "stardewvalley" ||
                uri.userInfo != null || uri.port != -1 || uri.rawFragment != null) return null
            val ids = pathPattern.matchEntire(uri.rawPath ?: "") ?: return null
            val query = uri.rawQuery ?: return null
            val pairs = query.split('&')
            if (pairs.size > 16) return null
            val params = linkedMapOf<String, String>()
            for (item in pairs) {
                val split = item.indexOf('=')
                if (split <= 0) return null
                val name = item.substring(0, split)
                if (name.length > 32 || !name.all { it.isLetterOrDigit() || it == '_' }) return null
                if (name in params) return null
                val value = URLDecoder.decode(item.substring(split + 1), StandardCharsets.UTF_8.name())
                if (value.length > 512 || value.any { it.code < 32 }) return null
                params[name] = value
            }
            val key = params["key"] ?: return null
            val expires = params["expires"] ?: return null
            if (!keyPattern.matches(key) || !expires.matches(Regex("[0-9]{1,12}"))) return null
            val expiry = expires.toLongOrNull() ?: return null
            if (expiry <= nowEpochSeconds || expiry > nowEpochSeconds + MAX_FUTURE_SECONDS) return null
            Request(ids.groupValues[1], ids.groupValues[2], key, expires)
        } catch (_: Exception) {
            null
        }
    }
}
