package com.sdvsync.mods

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Properties
import java.util.UUID

/** Never contains an authorization URL or credentials. */
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

/** A refusal is not a scheduled download; callers must not report a successful handoff. */
data class ModDownloadAdmission(val jobId: String? = null, val reason: String = "ACCEPTED") {
    val accepted: Boolean get() = jobId != null && reason == "ACCEPTED"
    val userMessage: String get() = when (reason) {
        "ACCEPTED" -> "Download queued for the selected Nexus file"
        "ALREADY_ACTIVE" -> "That exact file is already queued or downloading"
        "PAUSED" -> "That exact file is paused. Resume its existing download"
        "VERIFY_REQUIRED" -> "Previous installation outcome is uncertain. Inspect Mods and operation history"
        "REVIEW_PENDING" -> "That exact file awaits archive review; finish or discard the review first"
        "INVALID_IDENTITY" -> "Invalid exact Nexus file identity; select the file again"
        "QUEUE_FULL" -> "The protected download journal is full; resolve pending items"
        "STORAGE_UNAVAILABLE" -> "Cannot start download; check storage access"
        "START_FAILED" -> "Android could not start the download service"
        else -> "Download cannot start safely; inspect Downloads"
    }
}

class ModDownloadJournal(private val context: Context) {
    companion object {
        private const val PREFS = "cinderbox_mod_download_journal_v1"
        private const val KEY = "records"
        // Shared by all manager/journal instances within the Cinderbox process.
        private val lock = Any()
        val revision = MutableStateFlow(0L)
        private val active = setOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING")
        private val terminalStatuses = setOf("INSTALLED", "COMPLETED", "FAILED", "CANCELLED", "DISCARDED")
        private val protectedStatuses = active + setOf("PAUSED", "VERIFY_REQUIRED", "REVIEW_REQUIRED", "BLOCKED")
        private val known = active + terminalStatuses + setOf("REVIEW_REQUIRED", "BLOCKED", "PAUSED", "INTERRUPTED", "VERIFY_REQUIRED")
        private val positiveId = Regex("[1-9][0-9]{0,11}")
    }

    private val prefs get() = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private fun JSONObject.string(key: String, max: Int = 120): String = optString(key, "").take(max)

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
        return rows.sortedWith(compareBy<ModDownloadRecord> {
            if (it.status == "QUEUED") 0 else 1
        }.thenBy { if (it.status == "QUEUED") it.queuePosition else -it.createdAt }
            .thenBy { it.id }).toMutableList()
    }

    private fun write(rows: List<ModDownloadRecord>) {
        // Unresolved outcomes must NEVER fall out of the bounded history just because
        // many completed downloads were recorded later.
        val keep = rows.filter { it.status in protectedStatuses } +
            rows.filterNot { it.status in protectedStatuses }
        check(rows.count { it.status in protectedStatuses } <= 60) {
            "Too many unresolved download states; manual reconciliation required"
        }
        val json = JSONArray()
        for (row in keep.take(60)) {
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

    /** A durable review receipt also blocks admission if its journal row was lost/corrupted. */
    private fun hasUnresolvedReviewIdentity(source: String, modId: String, fileId: String): Boolean {
        if (source != "nexus") return false
        val root = context.filesDir
        val headZip = File(root, "mod-review-pending.zip")
        val headProps = File(root, "mod-review-pending.properties")
        val backlog = File(root, "mod-review-backlog")
        // A partially written/legacy head is ambiguous; refuse until reconciled.
        if (headZip.exists() != headProps.exists()) return true
        val candidates = mutableListOf<File>()
        if (headZip.exists()) candidates += headProps
        if (backlog.exists() && (!backlog.isDirectory || backlog.listFiles() == null)) return true
        backlog.listFiles()?.filter { it.isFile && !it.name.startsWith(".") }?.forEach { entry ->
            when {
                entry.name.endsWith(".zip") -> {
                    val receipt = File(backlog, entry.name.removeSuffix(".zip") + ".properties")
                    if (!receipt.isFile) return true
                    candidates += receipt
                }
                entry.name.endsWith(".properties") -> {
                    val archive = File(backlog, entry.name.removeSuffix(".properties") + ".zip")
                    if (!archive.isFile) return true
                }
            }
        }
        for (receipt in candidates) {
            if (receipt.length() > 32768L) return true
            val props = try {
                Properties().apply { receipt.inputStream().use { load(it) } }
            } catch (_: Exception) { return true }
            val storedSource = props.getProperty("source") ?: return true
            val storedMod = props.getProperty("mod_id") ?: return true
            val storedFile = props.getProperty("file_id") ?: return true
            if (storedSource == source && storedMod == modId && storedFile == fileId) return true
        }
        return false
    }

    /** Atomic check/allocate/persist under the SAME lock across manager instances. */
    fun admit(name: String, source: String, modId: String, fileId: String): ModDownloadAdmission = synchronized(lock) {
        if (source.isBlank() || source.length > 30 ||
            (source.equals("nexus", ignoreCase = true) && source != "nexus") ||
            (source == "nexus" && (!positiveId.matches(modId) || !positiveId.matches(fileId)))) {
            return@synchronized ModDownloadAdmission(reason = "INVALID_IDENTITY")
        }
        // An unreadable journal is never equivalent to an empty journal.
        if (runCatching { JSONArray(prefs.getString(KEY, "[]")) }.isFailure) {
            return@synchronized ModDownloadAdmission(reason = "JOURNAL_UNAVAILABLE")
        }
        val rows = parse()
        if (rows.count { it.status in protectedStatuses } >= 60) {
            return@synchronized ModDownloadAdmission(reason = "QUEUE_FULL")
        }
        if (source == "nexus") {
            val duplicate = rows.firstOrNull { it.source == source && it.modId == modId &&
                it.fileId == fileId && it.status in protectedStatuses }
            if (duplicate != null) {
                val reason = when (duplicate.status) {
                    "PAUSED" -> "PAUSED"
                    "VERIFY_REQUIRED" -> "VERIFY_REQUIRED"
                    "REVIEW_REQUIRED", "BLOCKED" -> "REVIEW_PENDING"
                    else -> "ALREADY_ACTIVE"
                }
                return@synchronized ModDownloadAdmission(reason = reason)
            }
            if (hasUnresolvedReviewIdentity(source, modId, fileId)) {
                return@synchronized ModDownloadAdmission(reason = "REVIEW_PENDING")
            }
        }
        val id = UUID.randomUUID().toString()
        val now = System.currentTimeMillis()
        val nextOrder = maxOf(now, (rows.maxOfOrNull { it.queuePosition } ?: 0L) + 1L)
        rows.add(0, ModDownloadRecord(id, name.take(120), source, modId.take(16),
            fileId.take(16), "QUEUED", 0, 0, now, now, "Waiting to download", nextOrder))
        write(rows)
        ModDownloadAdmission(jobId = id)
    }

    /** Legacy fixture/helper creation. Production download admission MUST use admit(). */
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

    fun isQueuedIdentity(id: String, source: String, modId: String, fileId: String): Boolean =
        synchronized(lock) { parse().any { it.id == id && it.status == "QUEUED" &&
            it.source == source && it.modId == modId && it.fileId == fileId } }

    private fun allowed(old: String, next: String): Boolean = when (old) {
        "QUEUED" -> next in setOf("QUEUED", "DOWNLOADING", "PAUSED", "CANCELLED", "FAILED", "INTERRUPTED")
        "DOWNLOADING" -> next in setOf("DOWNLOADING", "VALIDATING", "PAUSED", "CANCELLED", "FAILED", "INTERRUPTED")
        "VALIDATING" -> next in setOf("VALIDATING", "REVIEW_REQUIRED", "BLOCKED", "VERIFY_REQUIRED", "INSTALLING")
        "INSTALLING" -> next in setOf("INSTALLING", "INSTALLED", "VERIFY_REQUIRED")
        "REVIEW_REQUIRED", "BLOCKED" -> next == old || next == "INSTALLED" || next == "DISCARDED"
        "PAUSED" -> next in setOf("PAUSED", "CANCELLED", "INTERRUPTED")
        "VERIFY_REQUIRED", "INSTALLED", "COMPLETED", "FAILED", "CANCELLED", "DISCARDED", "INTERRUPTED" -> next == old
        else -> false
    }

    /** Monotonic safety transitions. A stale worker cannot downgrade VERIFY_REQUIRED/INSTALLED. */
    fun update(id: String, status: String, received: Long? = null, total: Long? = null,
               detail: String? = null): Boolean = synchronized(lock) {
        require(status in known) { "Invalid download status" }
        val rows = parse()
        val position = rows.indexOfFirst { it.id == id }
        if (position < 0) return@synchronized false
        val old = rows[position]
        if (!allowed(old.status, status)) return@synchronized false
        rows[position] = old.copy(status = status,
            received = (received ?: old.received).coerceAtLeast(0L),
            total = (total ?: old.total).coerceAtLeast(0L),
            updatedAt = System.currentTimeMillis(),
            detail = (detail ?: old.detail).take(180))
        write(rows)
        true
    }

    /** Only pending jobs may change order; validation and installation are immutable. */
    fun moveQueued(id: String, delta: Int): Boolean = synchronized(lock) {
        if (delta != -1 && delta != 1) return@synchronized false
        val rows = parse()
        val waiting = rows.filter { it.status == "QUEUED" }
        val position = waiting.indexOfFirst { it.id == id }
        if (!ModQueueControlPolicy.validMove(position, waiting.size, delta)) return@synchronized false
        val target = position + delta
        val a = rows.indexOfFirst { it.id == waiting[position].id }
        val b = rows.indexOfFirst { it.id == waiting[target].id }
        val first = rows[a]; val second = rows[b]
        rows[a] = first.copy(queuePosition = second.queuePosition)
        rows[b] = second.copy(queuePosition = first.queuePosition)
        write(rows)
        true
    }

    /** Same session and same UUID; an expired URL cannot be restored after process death. */
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

    /** Process restarts must never use expiring links or guess at install outcomes. */
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

    /** Never overwrites an installed, reviewed, cancelled or already-uncertain state. */
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

    /** Cancellation is allowed in TRANSFER only; not validation/installation. */
    fun cancelIfActive(id: String, reason: String) = synchronized(lock) {
        val rows = parse()
        val index = rows.indexOfFirst { it.id == id }
        if (index >= 0 && rows[index].status in setOf("QUEUED", "DOWNLOADING")) {
            rows[index] = rows[index].copy(status = "CANCELLED",
                updatedAt = System.currentTimeMillis(), detail = reason.take(180))
            write(rows)
        }
    }

    fun clearHistory() = synchronized(lock) {
        write(parse().filterNot { it.status in terminalStatuses })
    }
}
