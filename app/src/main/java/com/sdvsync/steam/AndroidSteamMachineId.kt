package com.sdvsync.steam

import android.content.Context
import java.nio.charset.StandardCharsets
import java.util.UUID

/**
 * Android-specific replacement for JavaSteam's Linux-specific system hardware probes.
 * Initialized before JavaSteam can invoke HardwareUtils.getMachineID().
 * Private, install-stable and never exported or logged.
 */
object AndroidSteamMachineId {
    @Volatile private var machineId: ByteArray? = null

    fun initialize(context: Context) {
        if (machineId != null) return
        synchronized(this) {
            if (machineId != null) return
            val prefs = context.applicationContext.getSharedPreferences("steam_android_identity", Context.MODE_PRIVATE)
            val stored = prefs.getString("machine_id", null)
            val value = stored?.takeIf { UUID_PATTERN.matches(it) }
                ?: UUID.randomUUID().toString().also { generated ->
                    check(prefs.edit().putString("machine_id", generated).commit()) {
                        "Could not persist Steam device identity"
                    }
                }
            machineId = ("Cinderbox-Android-" + value).toByteArray(StandardCharsets.UTF_8)
        }
    }

    @JvmStatic
    fun getMachineId(): ByteArray = checkNotNull(machineId) {
        "Steam machine identity not initialized"
    }.clone()

    private val UUID_PATTERN = Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
}
