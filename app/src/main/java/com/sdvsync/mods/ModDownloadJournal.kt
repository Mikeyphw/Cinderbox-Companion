package com.sdvsync.mods

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/** Credential-free, bounded, process-independent download records. Live Nexus URLs are NEVER saved. */
data class ModDownloadRecord(
    val id: String,
    val name: String,
    val source: String,
    val modId: String,
    val fileId: String,
    val status: String,
    val received: Long,
    val total: Long,
    val createdAt: Long,
    val updatedAt: Long,
    val detail: String
)

class ModDownloadJournal(private val context: Context) {
    companion object {
        private const val PREFS = "cinderbox_mod_download_journal_v1"
        private const val KEY = "records"
        private val lock = Any()
        val revision = MutableStateFlow(0L)
        private val active = setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING")
        private val terminalStatuses = setOf("INSTALLED", "COMPLETED", "FAILED", "CANCELLED", "DISCARDED")
        private val known = active + terminalStatuses + setOf("REVIEW_REQUIRED", "BLOCKED")
    }

    private val prefs get() = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun JSONObject.string(key: String, max: Int = 120): String =
        optString(key, "").take(max)

    private fun parse(): MutableList<ModDownloadRecord> {
        val rows = mutableListOf<ModDownloadRecord>()
        val data = try { JSONArray(prefs.getString(KEY, "[]")) } catch (_: Exception) { JSONArray() }
        for (n in 0 until minOf(data.length(), 80)) {
            val row = data.optJSONObject(n) ?: continue
            val id = row.string("id", 64)
            val status = row.string("status", 32)
            if (id.isBlank() || status !in known) continue
            rows += ModDownloadRecord(id, row.string("name"), row.string("source", 30),
                row.string("modId", 16), row.string("fileId", 16), status,
                row.optLong("received", 0L).coerceAtLeast(0L),
                row.optLong("total", 0L).coerceAtLeast(0L),
                row.optLong("created", 0L), row.optLong("updated", 0L),
                row.string("detail", 180))
        }
        return rows
    }

    private fun write(rows: List<ModDownloadRecord>) {
        val json = JSONArray()
        // No remote URL, request token, NXM key, local path, or Nexus credentials.
        for (row in rows.take(60)) {
            json.put(JSONObject().put("id", row.id).put("name", row.name)
                .put("source", row.source).put("modId", row.modId).put("fileId", row.fileId)
                .put("status", row.status).put("received", row.received)
                .put("total", row.total).put("created", row.createdAt)
                .put("updated", row.updatedAt).put("detail", row.detail))
        }
        check(prefs.edit().putString(KEY, json.toString()).commit()) {
            "Unable to persist download state"
        }
        revision.value = revision.value + 1L
    }

    fun list(): List<ModDownloadRecord> = synchronized(lock) { parse().toList() }

    fun create(name: String, source: String, modId: String, fileId: String): String = synchronized(lock) {
        val id = UUID.randomUUID().toString()
        val now = System.currentTimeMillis()
        val records = parse()
        records.add(0, ModDownloadRecord(id, name.take(120), source.take(30),
            modId.take(16), fileId.take(16), "QUEUED", 0, 0, now, now, "Waiting to download"))
        write(records)
        id
    }

    fun update(id: String, status: String, received: Long? = null, total: Long? = null,
               detail: String? = null) = synchronized(lock) {
        require(status in known) { "Invalid download status" }
        val rows = parse()
        val position = rows.indexOfFirst { it.id == id }
        if (position >= 0) {
            val old = rows[position]
            rows[position] = old.copy(status = status,
                received = (received ?: old.received).coerceAtLeast(0L),
                total = (total ?: old.total).coerceAtLeast(0L),
                updatedAt = System.currentTimeMillis(),
                detail = (detail ?: old.detail).take(180))
            write(rows)
        }
    }

    /** Process restarts cannot restore expiring Nexus links. Never invent a resumable URL. */
    fun markInterrupted() = synchronized(lock) {
        val old = parse()
        if (old.none { it.status in active }) return@synchronized
        write(old.map { row ->
            if (row.status in active) row.copy(status = "FAILED", updatedAt = System.currentTimeMillis(),
                detail = "Interrupted. Open the Nexus file again for fresh authorization.") else row
        })
    }

    fun cancelIfActive(id: String, reason: String) = synchronized(lock) {
        val rows = parse()
        val index = rows.indexOfFirst { it.id == id }
        if (index >= 0 && rows[index].status in active) {
            rows[index] = rows[index].copy(status = "CANCELLED",
                updatedAt = System.currentTimeMillis(), detail = reason.take(180))
            write(rows)
        }
    }

    fun clearHistory() = synchronized(lock) {
        write(parse().filterNot { it.status in terminalStatuses })
    }
}
