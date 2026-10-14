package com.sdvsync.steam

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.json.JSONArray
import org.json.JSONObject

/** Bounded, in-memory, token-free connection diagnostics. Never stores host, IP, account or tokens. */
object SteamDiagnostics {
    enum class Phase { OFFLINE, CONNECTING, AUTHENTICATING, CONNECTED, RECONNECTING }
    data class Event(val timeMs: Long, val phase: Phase, val message: String, val network: String)
    data class Snapshot(val phase: Phase, val sinceMs: Long, val events: List<Event>, val failures: Int)

    private const val HISTORY_MS = 3_600_000L
    private const val MAX_EVENTS = 180
    private val lock = Any()
    private val _snapshot = MutableStateFlow(Snapshot(Phase.OFFLINE, System.currentTimeMillis(), emptyList(), 0))
    val snapshot = _snapshot.asStateFlow()
    @Volatile private var context: Context? = null
    @Volatile var activeTransport: String = "unknown"
        private set

    fun setTransport(protocol: String) {
        activeTransport = when {
            protocol.contains("WEB_SOCKET") -> "WebSocket"
            protocol.contains("TCP") -> "TCP"
            else -> "unknown"
        }
    }
    fun trace(label: String) { record(snapshot.value.phase, label) }

    fun initialize(applicationContext: Context) {
        context = applicationContext.applicationContext
        val now = System.currentTimeMillis()
        // Restore only bounded, sanitized status events; history survives app restarts.
        runCatching {
            val raw = context!!.getSharedPreferences("steam_diagnostics_history", Context.MODE_PRIVATE)
                .getString("events", "[]") ?: "[]"
            val arr = JSONArray(raw)
            val restored = (0 until arr.length()).mapNotNull { i ->
                val obj = arr.optJSONObject(i) ?: return@mapNotNull null
                val time = obj.optLong("t")
                if (time !in (now - HISTORY_MS)..now) return@mapNotNull null
                val phase = runCatching { Phase.valueOf(obj.optString("p")) }.getOrNull()
                    ?: return@mapNotNull null
                Event(time, phase, obj.optString("e").take(80), obj.optString("n").take(100))
            }.takeLast(MAX_EVENTS)
            synchronized(lock) {
                _snapshot.value = Snapshot(Phase.OFFLINE, now, restored, restored.count {
                    it.message.endsWith("unexpectedly") || it.message.contains("timeout")
                })
            }
        }
    }

    fun networkSummary(): String = try {
        val cm = context?.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return "network_service_unavailable"
        val net = cm.activeNetwork ?: return "active_network_absent"
        val caps = cm.getNetworkCapabilities(net) ?: return "capabilities_absent"
        val transport = when {
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN) -> "vpn"
            else -> "other"
        }
        "$transport internet=${caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)} " +
            "validated=${caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)}"
    } catch (_: RuntimeException) {
        "network_query_error"
    }

    /** Messages must be constant, developer-authored labels; never pass external error text. */
    fun record(phase: Phase, label: String, failure: Boolean = false) {
        val now = System.currentTimeMillis()
        val network = networkSummary()
        synchronized(lock) {
            val old = _snapshot.value
            val events = (old.events.filter { it.timeMs >= now - HISTORY_MS } +
                Event(now, phase, label.take(80), network)).takeLast(MAX_EVENTS)
            _snapshot.value = Snapshot(
                phase, if (phase == old.phase) old.sinceMs else now,
                events, old.failures + if (failure) 1 else 0
            )
            val json = JSONArray()
            events.forEach { e -> json.put(JSONObject().put("t", e.timeMs).put("p", e.phase.name)
                .put("e", e.message).put("n", e.network)) }
            context?.getSharedPreferences("steam_diagnostics_history", Context.MODE_PRIVATE)
                ?.edit()?.putString("events", json.toString())?.apply()
        }
    }

    /** One-hour history sampled as one status bucket per minute. No sampling of private data. */
    fun minuteHistory(now: Long = System.currentTimeMillis()): List<Phase?> {
        val events = snapshot.value.events
        return (59 downTo 0).map { age ->
            val sampleAt = now - age * 60_000L
            events.lastOrNull { it.timeMs <= sampleAt }?.phase
        }
    }

    fun exportJson(): String {
        val s = snapshot.value
        val events = JSONArray()
        s.events.forEach { e ->
            events.put(JSONObject().put("time_ms", e.timeMs).put("phase", e.phase.name)
                .put("event", e.message).put("network", e.network))
        }
        return JSONObject().put("schema_version", 1).put("window_minutes", 60)
            .put("generated_at_ms", System.currentTimeMillis()).put("phase", s.phase.name)
            .put("failures", s.failures).put("transport", activeTransport)
            .put("events", events).toString(2)
    }
}
