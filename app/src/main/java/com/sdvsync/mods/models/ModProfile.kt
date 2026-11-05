package com.sdvsync.mods.models

import java.util.UUID

/** Profile identity is independent of its display name. Only metadata, never mod bytes. */
data class ModProfile(
    val name: String,
    val enabledModIds: Set<String>,
    val createdAt: Long = System.currentTimeMillis(),
    val id: String = UUID.randomUUID().toString(),
    val modifiedAt: Long = createdAt,
    val description: String = "",
    val isProtected: Boolean = false,
    val notes: Map<String, String> = emptyMap()
)
