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
    val detail: String,
    val queuePosition: Long = createdAt
)

class ModDownloadJournal(private val context: Context) {
    companion object {
        private const val PREFS = "cinderbox_mod_download_journal_v1"
        private const val KEY = "records"
        private val lock = Any()
        val revision = MutableStateFlow(0L)
        private val active = setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING")
        private val terminalStatuses = setOf("INSTALLED", "COMPLETED", "FAILED", "CANCELLED", "DISCARDED")
        private val known = active + terminalStatuses + setOf("REVIEW_REQUIRED", "BLOCKED", "PAUSED", "INTERRUPTED", "VERIFY_REQUIRED")
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
                row.string("detail", 180), row.optLong("queueOrder", row.optLong("created", 0L)))
        }
        // Active waiting jobs must appear in real FIFO order, not reverse history order.
        return rows.sortedWith(compareBy<ModDownloadRecord> {
            if (it.status == "QUEUED") 0 else 1
        }.thenBy { if (it.status == "QUEUED") it.queuePosition else -it.createdAt }
            .thenBy { it.id }).toMutableList()
    }

    private fun write(rows: List<ModDownloadRecord>) {
        val json = JSONArray()
        // No remote URL, request token, NXM key, local path, or Nexus credentials.
        for (row in rows.take(60)) {
            json.put(JSONObject().put("id", row.id).put("name", row.name)
                .put("source", row.source).put("modId", row.modId).put("fileId", row.fileId)
                .put("status", row.status).put("received", row.received)
                .put("total", row.total).put("created", row.createdAt)
                .put("updated", row.updatedAt).put("detail", row.detail)
                .put("queueOrder", row.queuePosition))
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
        val nextOrder = maxOf(now, (records.maxOfOrNull { it.queuePosition } ?: 0L) + 1L)
        records.add(0, ModDownloadRecord(id, name.take(120), source.take(30),
            modId.take(16), fileId.take(16), "QUEUED", 0, 0, now, now,
            "Waiting to download", nextOrder))
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

    /** Only pending jobs may change order; validation and installation are immutable. */
    fun moveQueued(id: String, delta: Int): Boolean = synchronized(lock) {
        if (delta != -1 && delta != 1) return@synchronized false
        val rows = parse()
        val waiting = rows.filter { it.status == "QUEUED" }
        val position = waiting.indexOfFirst { it.id == id }
        val target = position + delta
        if (!ModQueueControlPolicy.validMove(position, waiting.size, delta)) return@synchronized false
        val a = rows.indexOfFirst { it.id == waiting[position].id }
        val b = rows.indexOfFirst { it.id == waiting[target].id }
        val first = rows[a]; val second = rows[b]
        rows[a] = first.copy(queuePosition = second.queuePosition)
        rows[b] = second.copy(queuePosition = first.queuePosition)
        write(rows)
        true
    }

    /** Same-session resume is a new transfer, never an unverified partial ZIP. */
    fun resumePaused(id: String): Boolean = synchronized(lock) {
        val rows = parse()
        val pos = rows.indexOfFirst { it.id == id && it.status == "PAUSED" }
        if (pos < 0) return@synchronized false
        val previous = rows[pos]
        val nextOrder = maxOf(System.currentTimeMillis(), (rows.maxOfOrNull { it.queuePosition } ?: 0L) + 1L)
        rows[pos] = previous.copy(status = "QUEUED", received = 0L, total = 0L,
            updatedAt = System.currentTimeMillis(), queuePosition = nextOrder,
            detail = "Resuming from byte zero with this session's authorization")
        write(rows)
        true
    }

    /** Process restarts cannot restore expiring Nexus links. Never invent a resumable URL. */
    fun markInterrupted() = synchronized(lock) {
        val old = parse()
        if (old.none { it.status in active || it.status == "PAUSED" }) return@synchronized
        write(old.map { row ->
            when (row.status) {
                "QUEUED", "DOWNLOADING", "PAUSED" -> row.copy(status = "INTERRUPTED",
                    updatedAt = System.currentTimeMillis(), received = 0L, total = 0L,
                    detail = "Transfer interrupted. Open the exact Nexus file for fresh authorization.")
                "VALIDATING", "INSTALLING" -> row.copy(status = "VERIFY_REQUIRED",
                    updatedAt = System.currentTimeMillis(),
                    detail = "Outcome unknown. Inspect installed Mods and operation history before retrying.")
                else -> row
            }
        })
    }

    /** Reconciliation cannot overwrite an already-installed or reviewed receipt. */
    fun markJobInterrupted(id: String) = synchronized(lock) {
        val rows = parse()
        val index = rows.indexOfFirst { it.id == id }
        if (index < 0) return@synchronized
        val row = rows[index]
        val (next, reason) = when (row.status) {
            "QUEUED", "DOWNLOADING", "PAUSED" -> "INTERRUPTED" to
                "Transfer interrupted; reopen the exact Nexus file"
            "VALIDATING", "INSTALLING" -> "VERIFY_REQUIRED" to
                "Outcome unknown; inspect installed Mods and operations before retrying"
            else -> return@synchronized
        }
        rows[index] = row.copy(status = next, updatedAt = System.currentTimeMillis(),
            detail = reason, received = if (next == "INTERRUPTED") 0L else row.received,
            total = if (next == "INTERRUPTED") 0L else row.total)
        write(rows)
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
