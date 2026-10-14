package com.sdvsync.steam

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.sdvsync.MainActivity
import com.sdvsync.logging.AppLogger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import org.koin.android.ext.android.inject

/**
 * User-visible, user-disableable foreground Steam session.
 * A foreground service improves Android scheduling/background network eligibility;
 * it cannot override a disconnected Wi-Fi radio or vendor network restrictions.
 * Starts only from visible Activity code, never from a network callback.
 */
class SteamBackgroundService : Service() {
    companion object {
        private const val TAG = "SteamBackgroundService"
        private const val CHANNEL_ID = "steam_connection"
        private const val NOTIFICATION_ID = 12
        private const val PREFS = "steam_background_options"
        private const val KEY_ENABLED = "keep_steam_online"

        @Volatile private var active = false

        fun isEnabled(context: Context): Boolean = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(KEY_ENABLED, true)

        fun setEnabled(context: Context, enabled: Boolean) {
            context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean(KEY_ENABLED, enabled).apply()
            if (!enabled) stop(context)
        }

        /** Call only from a started, visible Activity, after Steam login. */
        fun start(context: Context) {
            if (!isEnabled(context) || active) return
            try {
                ContextCompat.startForegroundService(
                    context, Intent(context, SteamBackgroundService::class.java)
                )
            } catch (e: RuntimeException) {
                // Android may deny foreground-service starts. Reconnect still works in-app.
                AppLogger.w(TAG, "Steam foreground service could not start", e)
                SteamDiagnostics.trace("background_service_start_denied")
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, SteamBackgroundService::class.java))
        }
    }

    private val steamClient: SteamClientManager by inject()
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var updates: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        if (!isEnabled(this)) {
            stopSelf()
            return
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID, "Steam connection", NotificationManager.IMPORTANCE_LOW
            ).apply { description = "Keep the Steam session connected while Cinderbox is in the background" }
        )
        startForeground(NOTIFICATION_ID, notification("Keeping Steam connected"))
        active = true
        SteamDiagnostics.trace("background_service_started")
        updates = scope.launch {
            steamClient.connectionState.collect { state ->
                val message = when (state) {
                    ConnectionState.LOGGED_IN -> "Steam session connected"
                    ConnectionState.CONNECTING, ConnectionState.DISCONNECTING -> "Steam connection changing"
                    ConnectionState.CONNECTED -> "Authenticating with Steam"
                    ConnectionState.DISCONNECTED -> "Waiting to reconnect to Steam"
                }
                manager.notify(NOTIFICATION_ID, notification(message))
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isEnabled(this)) stopSelf(startId)
        // No background resurrection after the OS kills the process.
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        active = false
        updates?.cancel()
        scope.cancel()
        SteamDiagnostics.trace("background_service_stopped")
        super.onDestroy()
    }

    private fun notification(message: String): Notification {
        val openApp = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Cinderbox • Steam connection")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_popup_sync)
            .setContentIntent(openApp)
            .setOnlyAlertOnce(true)
            .setOngoing(true)
            .build()
    }
}
