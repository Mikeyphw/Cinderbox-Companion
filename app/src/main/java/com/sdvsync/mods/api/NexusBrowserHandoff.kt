package com.sdvsync.mods.api

import java.util.UUID

/** Cinderbox-owned bridge parameters; Nexus Mods does not interpret these values. */
object NexusBrowserHandoff {
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    private val safeRequestId = Regex("[A-Za-z0-9-]{8,64}")

    fun createUrl(modId: String, fileId: String, requestId: String = UUID.randomUUID().toString()): String? {
        if (!positiveId.matches(modId) || !positiveId.matches(fileId) ||
            !safeRequestId.matches(requestId)) return null
        return "https://www.nexusmods.com/stardewvalley/mods/$modId" +
            "?tab=files&cinderbox_file=$fileId&cinderbox_mode=nxm&cinderbox_request=$requestId"
    }
}
