package com.sdvsync

import android.app.Application
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.di.appModule
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.ModDownloadJournal
import com.sdvsync.logging.JavaSteamLogBridge
import com.sdvsync.steam.AndroidSteamMachineId
import com.sdvsync.steam.SteamDiagnostics
import `in`.dragonbra.javasteam.util.log.LogManager
import org.koin.android.ext.koin.androidContext
import org.koin.android.ext.koin.androidLogger
import org.koin.core.context.startKoin

class SdvSyncApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Must initialize before DI, AppLogger or any game path accessor is used.
        if (BuildConfig.CBNX_LAB) CinderboxLabBoundary.initialize(this)
        AppLogger.init(this)
        // Reconcile jobs left active by a previous killed app process.
        // Expiring Nexus links are not persisted and are never silently retried.
        runCatching { ModDownloadJournal(this).markInterrupted() }
        if (!BuildConfig.CBNX_LAB) {
            AndroidSteamMachineId.initialize(this)
            SteamDiagnostics.initialize(this)
        }
        patchVZipBufferPool()
        LogManager.addListener(JavaSteamLogBridge())
        startKoin {
            androidLogger()
            androidContext(this@SdvSyncApp)
            modules(appModule)
        }
    }

    /**
     * VZipUtil allocates an 8MB ThreadLocal per thread that touches decompression.
     * Replace with lazy allocation to avoid OOM on low-heap devices where Dispatchers.IO
     * rotates through many threads.
     */
    private fun patchVZipBufferPool() {
        try {
            val clazz = Class.forName("in.dragonbra.javasteam.util.VZipUtil")
            val field = clazz.getDeclaredField("windowBufferPool").apply { isAccessible = true }
            @Suppress("UNCHECKED_CAST")
            field.set(null, ThreadLocal.withInitial { ByteArray(0) })
        } catch (e: Exception) {
            AppLogger.w("SdvSyncApp", "Could not patch VZipUtil ThreadLocal", e)
        }
    }
}
