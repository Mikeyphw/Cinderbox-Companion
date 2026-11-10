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
            socket.connect(InetSocketAddress("127.0.0.1", NexusPairingBridge.PORT), 1500)
            socket.soTimeout = 1800
            val bytes = body.toByteArray(StandardCharsets.UTF_8)
            val prelude = buildString {
                append("$method $path HTTP/1.1\r\nHost: 127.0.0.1:${NexusPairingBridge.PORT}\r\n")
                if (method == "POST") append("Content-Type: application/json\r\nContent-Length: ${bytes.size}\r\n")
                for ((key, value) in headers) append("$key: $value\r\n")
                append("Connection: close\r\n\r\n")
            }
            socket.getOutputStream().write(prelude.toByteArray(StandardCharsets.US_ASCII) + bytes)
            socket.getOutputStream().flush()
            val raw = socket.getInputStream().readBytes().toString(StandardCharsets.UTF_8)
            val status = raw.substringBefore("\r\n").split(' ')[1].toInt()
            val payload = raw.substringAfter("\r\n\r\n")
            return status to (if (payload.isBlank()) JSONObject() else JSONObject(payload))
        }
    }

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
    }

    // Safe fixed-step failure labels; never include tokens, NXM URLs or response bodies.
    private fun <T> atStage(stage: String, block: () -> T): T = try {
        block()
    } catch (e: AssertionError) {
        throw AssertionError("CBNX03_SAFE_STAGE_$stage", e)
    } catch (e: Exception) {
        throw AssertionError("CBNX03_SAFE_STAGE_$stage", e)
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
        NexusPairingBridge.start(context)
        val token = pair()
        val h = mapOf("Authorization" to "Bearer $token", "X-CBNX-Nonce" to "ABCDEFGHIJKLMNOPQRSTUV")
        assertEquals(200, request("POST", "/v1/revoke", "{}", h).first)
        assertEquals(401, request("GET", "/v1/state", headers = h + ("X-CBNX-Nonce" to "ABCDEFGHIJKLMNOPQRSTUVW")).first)
        NexusPairingBridge.stop()
        assertFalse(NexusPairingBridge.snapshot().listening)
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
        NexusPairingBridge.start(context)
        val token = pair()
        val id = java.util.UUID.randomUUID().toString().replace("-", "")
        val body = JSONObject().put("mod_id", "50535").put("file_id", "178239")
            .put("request_id", id).toString()
        assertEquals(403, request("POST", "/v1/handoff", body, headers(token)).first)
        NexusPairingBridge.setHandoffEnabled(true)
        val accepted = request("POST", "/v1/handoff", body, headers(token))
        assertEquals(202, accepted.first)
        assertEquals("pending_user_action", accepted.second.getString("status"))
        assertFalse(accepted.second.getBoolean("download_started"))
        assertFalse(accepted.second.getBoolean("archive_staged"))
        assertFalse(accepted.second.getBoolean("installed"))
        val state = request("GET", "/v1/state", headers = headers(token))
        assertEquals(200, state.first)
        assertTrue(state.second.getBoolean("handoff_enabled"))
        assertTrue(state.second.getJSONArray("handoffs").toString().contains(id))
        assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "PENDING" })
        assertTrue(NexusPairingInbox.resolve(context, id, "DISMISSED"))
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
        NexusPairingBridge.start(context)
        val token = pair()
        NexusPairingBridge.setHandoffEnabled(true)
        val id = java.util.UUID.randomUUID().toString().replace("-", "")
        val body = JSONObject().put("mod_id", "50535").put("file_id", "190561")
            .put("request_id", id).toString()
        assertEquals(202, request("POST", "/v1/handoff", body, headers(token)).first)
        NexusPairingBridge.stop()
        assertFalse(NexusPairingBridge.snapshot().handoffEnabled)
        assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "PENDING" })
        assertTrue(NexusPairingInbox.resolve(context, id, "OPENED"))
        assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "OPENED" })
        // No ModDownloadJournal job can be produced by this request-only bridge.
        assertFalse(ModDownloadJournal(context).list().any { it.name == id })
    }

}
