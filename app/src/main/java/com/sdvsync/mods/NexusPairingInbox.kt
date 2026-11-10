package com.sdvsync.mods

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * CB-NX03B. App-private, credential-free, bounded requests for LOCAL user action.
 * Never enqueues a ModDownloadService job or touches the game directory.
 * Synchronous commit and one process lock prevent competing bridge requests from racing.
 */
internal object NexusPairingInbox {
    private val lock = Any()
    private const val PREFS = "cbnx03b_pairing_inbox"
    private const val KEY = "requests_v1"
    private const val MAX_PENDING = 8
    private const val MAX_HISTORY = 32
    private const val HISTORY_MS = 24 * 60 * 60 * 1000L
    private val positiveId = Regex("[1-9][0-9]{0,11}")
    private val requestId = Regex("[A-Za-z0-9_-]{22,64}")
    private val allowedStatuses = setOf("PENDING", "OPENED", "DISMISSED")

    data class Entry(val id: String, val modId: String, val fileId: String,
                     val status: String, val createdAt: Long)
    data class Admission(val state: String, val id: String)

    private fun read(context: Context): List<Entry> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val raw = checkNotNull(prefs.getString(KEY, "[]")) { "Missing inbox" }
        val array = JSONArray(raw)
        check(array.length() <= MAX_HISTORY + MAX_PENDING) { "Oversized inbox" }
        val entries = ArrayList<Entry>(array.length())
        val seen = HashSet<String>()
        for (i in 0 until array.length()) {
            val obj = checkNotNull(array.optJSONObject(i)) { "Invalid inbox entry" }
            val id = obj.getString("id")
            val mod = obj.getString("mod_id")
            val file = obj.getString("file_id")
            val status = obj.getString("status")
            val timestamp = obj.getLong("created_at")
            check(requestId.matches(id) && positiveId.matches(mod) && positiveId.matches(file) &&
                status in allowedStatuses && timestamp > 0 && seen.add(id)) { "Corrupt inbox entry" }
            entries.add(Entry(id, mod, file, status, timestamp))
        }
        return entries
    }

    private fun commit(context: Context, entries: List<Entry>): Boolean {
        val array = JSONArray()
        entries.forEach { e -> array.put(JSONObject()
            .put("id", e.id).put("mod_id", e.modId).put("file_id", e.fileId)
            .put("status", e.status).put("created_at", e.createdAt)) }
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, array.toString()).commit()
    }

    /** Never silently reset corrupted storage: fail closed instead of admitting duplicates. */
    fun list(context: Context): List<Entry> = synchronized(lock) { read(context) }

    fun admit(context: Context, id: String, modId: String, fileId: String): Admission = synchronized(lock) {
        if (!requestId.matches(id) || !positiveId.matches(modId) || !positiveId.matches(fileId))
            return@synchronized Admission("invalid_identity", "")
        val now = System.currentTimeMillis()
        val entries = read(context).filter {
            it.status == "PENDING" || (it.createdAt <= now && now - it.createdAt <= HISTORY_MS)
        }.toMutableList()
        val alreadyUsed = entries.find { it.id == id }
        if (alreadyUsed != null) {
            return@synchronized Admission(
                if (alreadyUsed.modId == modId && alreadyUsed.fileId == fileId) "already_seen" else "identity_conflict",
                alreadyUsed.id)
        }
        val pending = entries.find { it.modId == modId && it.fileId == fileId && it.status == "PENDING" }
        if (pending != null) return@synchronized Admission("already_pending", pending.id)
        if (entries.count { it.status == "PENDING" } >= MAX_PENDING)
            return@synchronized Admission("inbox_full", "")
        entries.add(Entry(id, modId, fileId, "PENDING", now))
        // Retain pending entries indefinitely until explicitly resolved; bound recent history.
        val keep = entries.filter { it.status == "PENDING" } +
            entries.filter { it.status != "PENDING" }.takeLast(MAX_HISTORY)
        check(commit(context, keep)) { "Could not persist pairing inbox" }
        Admission("pending_user_action", id)
    }

    /** Only a local Android UI action may mark a request opened or dismissed. */
    fun resolve(context: Context, id: String, status: String): Boolean = synchronized(lock) {
        require(status == "OPENED" || status == "DISMISSED")
        val entries = read(context)
        if (entries.none { it.id == id && it.status == "PENDING" }) return@synchronized false
        check(commit(context, entries.map { if (it.id == id) it.copy(status = status) else it })) {
            "Could not persist inbox resolution"
        }
        true
    }
}
