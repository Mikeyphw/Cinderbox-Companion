package com.sdvsync.mods

import android.content.Context
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.LinkedHashMap
import java.util.LinkedHashSet

/** CB-NX03A: opt-in, in-process, read-only browser pairing. No install/control endpoint exists. */
internal object NexusPairingBridge {
    const val PORT = 38471
    private const val WINDOW_MS = 10 * 60_000L
    private const val CODE_MS = 2 * 60_000L
    private const val CHALLENGE_MS = 60_000L
    private val guard = Any()
    private val random = SecureRandom()
    private var listener: ServerSocket? = null
    private var token: String? = null
    private var code: String? = null
    private var codeDeadline = 0L
    private var windowDeadline = 0L
    private var connected = false
    private var guesses = 0
    private val challenges = LinkedHashMap<String, Long>()
    private val nonces = LinkedHashSet<String>()
    data class Snapshot(val listening: Boolean, val code: String?, val connected: Boolean,
                        val remainingSeconds: Long)

    private fun now() = System.currentTimeMillis()
    private fun randomString(bytes: Int): String = ByteArray(bytes).also(random::nextBytes).let {
        Base64.encodeToString(it, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
    }
    private fun same(a: String, b: String): Boolean = MessageDigest.isEqual(
        a.toByteArray(StandardCharsets.US_ASCII), b.toByteArray(StandardCharsets.US_ASCII))

    fun snapshot(): Snapshot = synchronized(guard) {
        val time = now()
        Snapshot(listener != null && !listener!!.isClosed && time < windowDeadline,
            code?.takeIf { time < codeDeadline && token == null }, connected,
            ((windowDeadline - time).coerceAtLeast(0L) + 999L) / 1000L)
    }

    fun start(context: Context): Snapshot = synchronized(guard) {
        stopLocked()
        // Explicit pre-bind reuse prevents transient Android emulator TIME_WAIT bind failures.
        // Bind remains IPv4 loopback-only; never expose this listener on a LAN interface.
        val socket = ServerSocket().apply {
            reuseAddress = true
            bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)
            soTimeout = 1000
        }
        listener = socket
        windowDeadline = now() + WINDOW_MS
        codeDeadline = now() + CODE_MS
        code = (100_000_000 + random.nextInt(900_000_000)).toString()
        val appContext = context.applicationContext
        Thread({ serve(appContext, socket) }, "cbnx03-loopback").apply {
            isDaemon = true
            start()
        }
        snapshot()
    }

    fun revoke() = synchronized(guard) {
        token = null
        connected = false
        nonces.clear()
        // A new pairing requires deliberate local user action and a fresh code.
        code = null
        challenges.clear()
    }

    fun stop() = synchronized(guard) { stopLocked() }
    private fun stopLocked() {
        listener?.close()
        listener = null
        token = null
        code = null
        connected = false
        guesses = 0
        challenges.clear()
        nonces.clear()
        windowDeadline = 0L
        codeDeadline = 0L
    }

    private fun serve(context: Context, socket: ServerSocket) {
        while (true) {
            synchronized(guard) {
                if (listener !== socket) return
                if (now() >= windowDeadline) { stopLocked(); return }
            }
            val client = try { socket.accept() }
                catch (_: SocketTimeoutException) { continue }
                catch (_: Exception) { return }
            try {
                client.use {
                    it.soTimeout = 2200
                    handle(context, it)
                }
            } catch (_: Exception) {
                // Never log HTTP headers, pairing secrets, requests or provider data.
            }
        }
    }

    private fun readLineBounded(input: BufferedInputStream, limit: Int): String? {
        val bytes = ArrayList<Byte>()
        while (bytes.size <= limit) {
            val value = input.read()
            if (value < 0) return null
            if (value == 10) {
                if (bytes.lastOrNull() == 13.toByte()) bytes.removeAt(bytes.lastIndex)
                return String(bytes.toByteArray(), StandardCharsets.US_ASCII)
            }
            if (value < 32 && value != 13) return null
            bytes.add(value.toByte())
        }
        return null
    }

    private fun handle(context: Context, client: Socket) {
        if (!client.inetAddress.isLoopbackAddress) return
        val input = BufferedInputStream(client.getInputStream())
        val output = BufferedOutputStream(client.getOutputStream())
        val request = readLineBounded(input, 240) ?: return
        val parts = request.split(' ')
        if (parts.size != 3 || parts[2] != "HTTP/1.1") return
        val method = parts[0]
        val path = parts[1]
        val headers = mutableMapOf<String, String>()
        var total = 0
        for (i in 0 until 32) {
            val line = readLineBounded(input, 512) ?: return
            total += line.length
            if (total > 4096) return
            if (line.isEmpty()) break
            val at = line.indexOf(':')
            if (at < 1) return
            val key = line.substring(0, at).lowercase()
            if (headers.containsKey(key)) {
                // Duplicate Host / Origin / Authorization are denied explicitly, not by
                // silently closing: callers receive deterministic fail-closed 403.
                respond(output, 403, JSONObject().put("error", "refused"), null)
                return
            }
            headers[key] = line.substring(at + 1).trim()
        }
        val origin = headers["origin"]
        // Browser background sends Origin absent or moz-extension://<unique-id>.
        // Web pages cannot opt into CORS or use this endpoint with credentials.
        val allowedOrigin = origin == null || Regex("moz-extension://[0-9a-fA-F-]{36}").matches(origin)
        if (!allowedOrigin || headers["host"] != "127.0.0.1:$PORT" ||
            headers.containsKey("transfer-encoding")) {
            respond(output, 403, JSONObject().put("error", "refused"), null)
            return
        }
        if (method == "OPTIONS") {
            respond(output, 204, JSONObject(), origin)
            return
        }
        val body = if (method == "POST") {
            if (headers["content-type"]?.substringBefore(';') != "application/json") {
                respond(output, 415, JSONObject().put("error", "format"), origin); return
            }
            val size = headers["content-length"]?.toIntOrNull()
            if (size == null || size !in 2..1024) {
                respond(output, 413, JSONObject().put("error", "size"), origin); return
            }
            val raw = ByteArray(size)
            var n = 0
            while (n < raw.size) {
                val got = input.read(raw, n, raw.size - n)
                if (got <= 0) return
                n += got
            }
            try { JSONObject(String(raw, StandardCharsets.UTF_8)) }
                catch (_: Exception) { respond(output, 400, JSONObject().put("error", "json"), origin); return }
        } else JSONObject()
        val result: Pair<Int, JSONObject> = synchronized(guard) {
            val time = now()
            challenges.entries.removeAll { it.value < time }
            when {
                listener == null || time >= windowDeadline -> 503 to JSONObject().put("error", "offline")
                method == "GET" && path == "/v1/hello" -> {
                    val challenge = randomString(18)
                    if (challenges.size >= 8) challenges.remove(challenges.keys.first())
                    challenges[challenge] = time + CHALLENGE_MS
                    200 to JSONObject().put("protocol", 1).put("challenge", challenge)
                        .put("read_only", true)
                }
                method == "POST" && path == "/v1/pair" -> {
                    val codeSent = body.optString("code")
                    val challengeSent = body.optString("challenge")
                    val validChallenge = challenges.remove(challengeSent)?.let { it >= time } ?: false
                    val valid = validChallenge && code != null && time < codeDeadline &&
                        guesses < 5 && codeSent.length == 9 && same(codeSent, code!!)
                    if (valid && token == null) {
                        token = randomString(32)
                        code = null
                        connected = true
                        challenges.clear()
                        nonces.clear()
                        200 to JSONObject().put("protocol", 1).put("token", token).put("read_only", true)
                    } else {
                        guesses++
                        if (guesses >= 5) { code = null; challenges.clear() }
                        403 to JSONObject().put("error", "pair_refused")
                    }
                }
                method == "GET" && path == "/v1/state" ||
                    method == "POST" && path == "/v1/revoke" -> {
                    val supplied = headers["authorization"]?.removePrefix("Bearer ") ?: ""
                    val nonce = headers["x-cbnx-nonce"] ?: ""
                    if (token == null || !same(supplied, token!!) ||
                        !Regex("[A-Za-z0-9_-]{22,64}").matches(nonce) || nonces.size >= 128 ||
                        !nonces.add(nonce)) {
                        if (nonces.size >= 128) { token = null; connected = false; nonces.clear() }
                        401 to JSONObject().put("error", "unauthorized")
                    } else {
                        if (method == "POST") {
                            token = null
                            connected = false
                            code = null
                            nonces.clear()
                            200 to JSONObject().put("revoked", true)
                        } else {
                            connected = true
                            val jobs = JSONArray()
                            ModDownloadJournal(context).list().take(60).forEach { job ->
                                jobs.put(JSONObject().put("job_id", job.id.take(64))
                                    .put("source", job.source.take(32))
                                    .put("mod_id", job.modId.take(30))
                                    .put("file_id", job.fileId.take(30))
                                    .put("status", job.status.take(32))
                                    .put("received", job.received.coerceAtLeast(0))
                                    .put("total", job.total.coerceAtLeast(0)))
                            }
                            200 to JSONObject().put("protocol", 1).put("proof_kind", "journal_only")
                                .put("installed_inventory_qualified", false)
                                .put("jobs", jobs)
                        }
                    }
                }
                else -> 404 to JSONObject().put("error", "not_found")
            }
        }
        respond(output, result.first, result.second, origin)
    }

    private fun respond(output: BufferedOutputStream, code: Int, data: JSONObject, origin: String?) {
        val body = if (code == 204) ByteArray(0)
                   else data.toString().toByteArray(StandardCharsets.UTF_8)
        val message = when(code) { 200 -> "OK"; 204 -> "No Content"; 400 -> "Bad Request";
            401 -> "Unauthorized"; 403 -> "Forbidden"; 404 -> "Not Found";
            413 -> "Content Too Large"; 415 -> "Unsupported Media Type"; else -> "Unavailable" }
        val head = buildString {
            append("HTTP/1.1 $code $message\r\n")
            append("Content-Type: application/json; charset=utf-8\r\n")
            append("Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n")
            append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n")
            append("Access-Control-Allow-Headers: authorization, content-type, x-cbnx-nonce\r\n")
            if (origin != null) append("Access-Control-Allow-Origin: $origin\r\nVary: Origin\r\n")
            append("Content-Length: ${body.size}\r\nConnection: close\r\n\r\n")
        }
        output.write(head.toByteArray(StandardCharsets.US_ASCII))
        output.write(body)
        output.flush()
    }
}
