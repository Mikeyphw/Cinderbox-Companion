package com.sdvsync.mods

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.net.InetSocketAddress
import java.net.Socket
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.nio.charset.StandardCharsets

/** Synthetic localhost-only test: no Nexus, real Mods writes or provider credentials. */
@RunWith(AndroidJUnit4::class)
class CbNx03PairingDeviceTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Before fun before() { NexusPairingBridge.stop() }
    @After fun after() { NexusPairingBridge.stop() }

    private fun request(method: String, path: String, body: String = "",
                        headers: Map<String, String> = emptyMap()): Pair<Int, JSONObject> {
        Socket().use { socket ->
            socket.connect(InetSocketAddress("127.0.0.1", NexusPairingBridge.PORT), 5000)
            socket.soTimeout = 8000
            val bytes = body.toByteArray(StandardCharsets.UTF_8)
            val prelude = buildString {
                append("$method $path HTTP/1.1\r\nHost: 127.0.0.1:${NexusPairingBridge.PORT}\r\n")
                if (method == "POST") append("Content-Type: application/json\r\nContent-Length: ${bytes.size}\r\n")
                for ((key, value) in headers) append("$key: $value\r\n")
                append("Connection: close\r\n\r\n")
            }
            socket.getOutputStream().write(prelude.toByteArray(StandardCharsets.US_ASCII) + bytes)
            socket.getOutputStream().flush()
            // The old readBytes() waited for TCP close on a heavily loaded API36 emulator.
            // Read exactly the bounded Content-Length instead, without relaxing any HTTP assertion.
            val input = BufferedInputStream(socket.getInputStream())
            val head = ByteArrayOutputStream()
            val terminator = byteArrayOf(13, 10, 13, 10)
            while (head.size() < 8192) {
                val b = input.read()
                require(b >= 0) { "CBNX03_TRUNCATED_HTTP_HEADERS" }
                head.write(b)
                val bytesRead = head.toByteArray()
                if (bytesRead.size >= 4 && bytesRead.takeLast(4).toByteArray().contentEquals(terminator)) break
            }
            require(head.size() < 8192) { "CBNX03_OVERSIZED_HTTP_HEADERS" }
            val lines = head.toString(StandardCharsets.US_ASCII.name()).split("\r\n")
            val statusLine = lines.first().split(' ')
            require(statusLine.size >= 3 && statusLine[0] == "HTTP/1.1") { "CBNX03_INVALID_HTTP_STATUS" }
            val status = statusLine[1].toInt()
            val lengths = lines.filter { it.startsWith("Content-Length:", ignoreCase = true) }
            require(lengths.size == 1) { "CBNX03_INVALID_CONTENT_LENGTH_COUNT" }
            val length = lengths.single().substringAfter(':').trim().toInt()
            require(length in 0..65536) { "CBNX03_UNBOUNDED_HTTP_BODY" }
            val bodyBytes = ByteArray(length)
            var offset = 0
            while (offset < length) {
                val count = input.read(bodyBytes, offset, length - offset)
                require(count > 0) { "CBNX03_TRUNCATED_HTTP_BODY" }
                offset += count
            }
            val payload = String(bodyBytes, StandardCharsets.UTF_8)
            return status to (if (payload.isBlank()) JSONObject() else JSONObject(payload))
        }
    }

    // Isolate tests by exact Nexus identity rather than deleting durable user inbox data.
    // The real inbox still handles duplicate/replay behavior within each individual test.
    private fun distinctFixtureFile(): String =
        (100_000_000L + (java.security.SecureRandom().nextInt(900_000_000)).toLong()).toString()

    private fun pair(): String {
        val hello = request("GET", "/v1/hello")
        assertEquals(200, hello.first)
        val code = requireNotNull(NexusPairingBridge.snapshot().code)
        val body = JSONObject().put("code", code).put("challenge", hello.second.getString("challenge"))
        val response = request("POST", "/v1/pair", body.toString())
        assertEquals(200, response.first)
        return response.second.getString("token")
    }

    @Test fun optInRequiredAndLoopbackOnly() {
        assertFalse(NexusPairingBridge.snapshot().listening)
        val snapshot = NexusPairingBridge.start(context)
        assertTrue(snapshot.listening)
        assertEquals(9, requireNotNull(snapshot.code).length)
        assertEquals(403, request("GET", "/v1/hello", headers = mapOf("Origin" to "https://evil.example")).first)
        assertEquals(403, request("GET", "/v1/hello", headers = mapOf("Host" to "evil.example")).first)
        // HTTP field names are case-insensitive; reject a mixed-case duplicate too.
        assertEquals(403, request("GET", "/v1/hello", headers = mapOf("hOsT" to "evil.example")).first)
        // Repeated explicit stop/start must retain loopback-only binding.
        // This exercises the previously failing HANDOFF_START lifecycle without
        // changing the exact seven-method roster or touching durable game data.
        repeat(4) {
            NexusPairingBridge.stop()
            assertFalse(NexusPairingBridge.snapshot().listening)
            val rebound = NexusPairingBridge.start(context)
            assertTrue(rebound.listening)
            assertEquals(200, request("GET", "/v1/hello").first)
        }
    }

    // Safe fixed-step failure labels; never include tokens, NXM URLs or response bodies.
    private fun safeCause(error: Throwable): String {
        var current: Throwable? = error
        repeat(5) {
            when (current) {
                is java.net.BindException -> return "BIND_IN_USE"
                is java.net.SocketTimeoutException -> return "TIMEOUT"
                is java.net.SocketException -> return "SOCKET_FAILURE"
                is SecurityException -> return "SECURITY"
                is InterruptedException -> return "INTERRUPTED"
                is AssertionError -> return "ASSERTION"
            }
            current = current?.cause
        }
        return "OTHER"
    }

    private fun <T> atStage(stage: String, block: () -> T): T = try {
        block()
    } catch (e: AssertionError) {
        throw AssertionError("CBNX03_SAFE_STAGE_$stage CBNX03_SAFE_CAUSE_${safeCause(e)}", e)
    } catch (e: Exception) {
        throw AssertionError("CBNX03_SAFE_STAGE_$stage CBNX03_SAFE_CAUSE_${safeCause(e)}", e)
    }

    @Test fun pairingReadOnlyAndNonceReplayFails() {
        atStage("START") { NexusPairingBridge.start(context) }
        val token = atStage("PAIR") { pair() }
        val headers = mapOf("Authorization" to "Bearer $token", "X-CBNX-Nonce" to "ABCDEFGHIJKLMNOPQRSTUV")
        val state = atStage("STATE_FETCH") { request("GET", "/v1/state", headers = headers) }
        atStage("STATE_ASSERT") {
            assertEquals(200, state.first)
            assertEquals("journal_only", state.second.getString("proof_kind"))
            assertFalse(state.second.getBoolean("installed_inventory_qualified"))
        }
        atStage("NONCE_REPLAY") {
            assertEquals(401, request("GET", "/v1/state", headers = headers).first)
        }
        atStage("NO_INSTALL_ENDPOINT") {
            assertEquals(404, request("POST", "/v1/install", "{}", headers).first)
        }
    }

    @Test fun revokeInvalidatesTokenAndStopsListening() {
        atStage("REVOKE_START") { NexusPairingBridge.start(context) }
        val token = atStage("REVOKE_PAIR") { pair() }
        val h = mapOf("Authorization" to "Bearer $token", "X-CBNX-Nonce" to "ABCDEFGHIJKLMNOPQRSTUV")
        atStage("REVOKE_ACCEPTED") {
            assertEquals(200, request("POST", "/v1/revoke", "{}", h).first)
        }
        atStage("REVOKE_OLD_TOKEN_DENIED") {
            assertEquals(401, request("GET", "/v1/state", headers = h + ("X-CBNX-Nonce" to "ABCDEFGHIJKLMNOPQRSTUVW")).first)
        }
        atStage("REVOKE_STOP") {
            NexusPairingBridge.stop()
            assertFalse(NexusPairingBridge.snapshot().listening)
        }
    }

    @Test fun incorrectCodesLockOutPairing() {
        NexusPairingBridge.start(context)
        for (i in 0 until 5) {
            val challenge = request("GET", "/v1/hello").second.getString("challenge")
            val invalid = JSONObject().put("code", "000000000").put("challenge", challenge)
            assertEquals(403, request("POST", "/v1/pair", invalid.toString()).first)
        }
        assertNull(NexusPairingBridge.snapshot().code)
        val challenge = request("GET", "/v1/hello").second.getString("challenge")
        assertEquals(403, request("POST", "/v1/pair",
            JSONObject().put("code", "123456789").put("challenge", challenge).toString()).first)
    }

    private fun headers(token: String, nonce: String = java.util.UUID.randomUUID().toString().replace("-", "")) =
        mapOf("Authorization" to "Bearer $token", "X-CBNX-Nonce" to nonce)

    @Test fun exactFileHandoffRequiresLocalOptInAndNeverStartsDownload() {
        atStage("HANDOFF_START") { NexusPairingBridge.start(context) }
        val token = atStage("HANDOFF_PAIR") { pair() }
        val id = java.util.UUID.randomUUID().toString().replace("-", "")
        val fileId = distinctFixtureFile()
        val body = JSONObject().put("mod_id", "50535").put("file_id", fileId)
            .put("request_id", id).toString()
        atStage("HANDOFF_OPT_IN_GUARD") {
            assertEquals(403, request("POST", "/v1/handoff", body, headers(token)).first)
        }
        atStage("HANDOFF_LOCAL_ENABLE") { NexusPairingBridge.setHandoffEnabled(true) }
        atStage("HANDOFF_ADMISSION") {
            val accepted = request("POST", "/v1/handoff", body, headers(token))
            assertEquals(202, accepted.first)
            assertEquals("pending_user_action", accepted.second.getString("status"))
            assertFalse(accepted.second.getBoolean("download_started"))
            assertFalse(accepted.second.getBoolean("archive_staged"))
            assertFalse(accepted.second.getBoolean("installed"))
        }
        atStage("HANDOFF_STATE") {
            val state = request("GET", "/v1/state", headers = headers(token))
            assertEquals(200, state.first)
            assertTrue(state.second.getBoolean("handoff_enabled"))
            assertTrue(state.second.getJSONArray("handoffs").toString().contains(id))
        }
        atStage("HANDOFF_RESOLVE") {
            assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "PENDING" })
            assertTrue(NexusPairingInbox.resolve(context, id, "DISMISSED"))
        }
    }

    @Test fun invalidIdentityReplayAndConcurrentDuplicateAreFailClosed() {
        NexusPairingBridge.start(context)
        val token = pair()
        NexusPairingBridge.setHandoffEnabled(true)
        val id = java.util.UUID.randomUUID().toString().replace("-", "")
        fun submit(mod: String, file: String, requestId: String) = request("POST", "/v1/handoff",
            JSONObject().put("mod_id", mod).put("file_id", file).put("request_id", requestId).toString(),
            headers(token))
        assertEquals(400, submit("0", "178239", id).first)
        assertEquals(400, submit("50535", "1/2", id).first)
        assertEquals(400, submit("50535", "178239", "tiny").first)
        val accepted = submit("50535", "178239", id)
        assertEquals(202, accepted.first)
        assertEquals("pending_user_action", accepted.second.getString("status"))
        assertEquals("already_seen", submit("50535", "178239", id).second.getString("status"))
        assertEquals(409, submit("50535", "190561", id).first)
        val other = java.util.UUID.randomUUID().toString().replace("-", "")
        assertEquals("already_pending", submit("50535", "178239", other).second.getString("status"))
        assertEquals(id, NexusPairingInbox.list(context).first { it.id == id }.id)
        assertTrue(NexusPairingInbox.resolve(context, id, "DISMISSED"))
        assertEquals("already_seen", submit("50535", "178239", id).second.getString("status"))
    }

    @Test fun inboxSurvivesBridgeShutdownWithoutReenqueuingAnything() {
        atStage("INBOX_START") { NexusPairingBridge.start(context) }
        val token = atStage("INBOX_PAIR") { pair() }
        val id = java.util.UUID.randomUUID().toString().replace("-", "")
        val body = JSONObject().put("mod_id", "50535").put("file_id", distinctFixtureFile())
            .put("request_id", id).toString()
        atStage("INBOX_OPT_IN") { NexusPairingBridge.setHandoffEnabled(true) }
        atStage("INBOX_ADMISSION") {
            assertEquals(202, request("POST", "/v1/handoff", body, headers(token)).first)
        }
        atStage("INBOX_STOP") {
            NexusPairingBridge.stop()
            assertFalse(NexusPairingBridge.snapshot().handoffEnabled)
        }
        atStage("INBOX_DURABILITY") {
            assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "PENDING" })
            assertTrue(NexusPairingInbox.resolve(context, id, "OPENED"))
            assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "OPENED" })
        }
        // No ModDownloadJournal job can be produced by this request-only bridge.
        atStage("INBOX_NO_DOWNLOAD") {
            assertFalse(ModDownloadJournal(context).list().any { it.name == id })
        }
    }

}
