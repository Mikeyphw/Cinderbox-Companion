package com.sdvsync.mods.api

import java.net.URI
import java.util.Locale

/** Only verified browser routes; does not claim undocumented per-mod media/comment APIs. */
object NexusModPageLinks {
    private val positiveModId = Regex("[1-9][0-9]{0,11}")
    private val dnsName = Regex("(?i)[a-z0-9-]+(?:\\.[a-z0-9-]+)+")
    private val ipv4 = Regex("[0-9]+(?:\\.[0-9]+){3}")
    private val allowedTabs = setOf("posts", "images", "videos", "files")

    fun forTab(modId: String, tab: String): String? {
        if (!positiveModId.matches(modId) || tab !in allowedTabs) return null
        return "https://www.nexusmods.com/stardewvalley/mods/$modId?tab=$tab"
    }

    /** Reject deep-link schemes, local/private hostnames, credentials and custom ports. */
    fun safeExternalHttps(raw: String?): String? {
        if (raw.isNullOrBlank() || raw.length > 2048 || raw.any { it.code < 32 }) return null
        return try {
            val uri = URI(raw.trim())
            val host = uri.host?.lowercase(Locale.ROOT) ?: return null
            val labels = host.split('.')
            if (!uri.scheme.equals("https", ignoreCase = true) ||
                uri.userInfo != null || uri.port != -1 ||
                !dnsName.matches(host) || ipv4.matches(host) ||
                labels.any { it.startsWith('-') || it.endsWith('-') } ||
                labels.last().length < 2 || !labels.last().all(Char::isLetter) ||
                host == "localhost" || host.endsWith(".local") ||
                host.endsWith(".internal") || host.endsWith(".invalid") ||
                host.endsWith(".test") || host.endsWith(".example")
            ) null else uri.toASCIIString()
        } catch (_: Exception) {
            null
        }
    }
}
