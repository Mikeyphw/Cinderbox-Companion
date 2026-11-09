package com.sdvsync.mods.api

/** Pure and fail-closed navigation policy. Validation never makes network requests. */
object NexusIdJumpPolicy {
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    data class Destination(val modId: String, val fileId: String?)

    fun parse(modInput: String, fileInput: String = ""): Destination? {
        val modId = modInput.trim()
        val fileId = fileInput.trim()
        if (!positiveId.matches(modId) || (fileId.isNotEmpty() && !positiveId.matches(fileId))) {
            return null
        }
        return Destination(modId, fileId.ifEmpty { null })
    }
}
