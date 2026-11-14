package com.sdvsync.mods

/** LAB03C: build only an official Nexus FILES-page hint, never a signed download/NXM URL. */
internal object NexusLab03CPolicy {
    const val MAX_REQUEST_AGE_MS = 10 * 60 * 1000L
    private val positiveId = Regex("[1-9][0-9]{0,11}")

    fun canonicalUrl(modId: String, fileId: String): String? {
        if (!positiveId.matches(modId) || !positiveId.matches(fileId)) return null
        // file_id is a page hint; Nexus must independently confirm the selected file.
        return "https://www.nexusmods.com/stardewvalley/mods/$modId?tab=files&file_id=$fileId"
    }

    fun reviewUrl(modId: String, fileId: String, createdAt: Long, now: Long): String? {
        if (createdAt <= 0L || now <= 0L || createdAt > now ||
            now - createdAt > MAX_REQUEST_AGE_MS) return null
        return canonicalUrl(modId, fileId)
    }
}
