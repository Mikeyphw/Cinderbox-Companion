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
    }

    @Test fun pairingReadOnlyAndNonceReplayFails() {
        NexusPairingBridge.start(context)
        val token = pair()
        val headers = mapOf("Authorization" to "Bearer $token", "X-CBNX-Nonce" to "ABCDEFGHIJKLMNOPQRSTUV")
        val state = request("GET", "/v1/state", headers = headers)
        assertEquals(200, state.first)
        assertEquals("journal_only", state.second.getString("proof_kind"))
        assertFalse(state.second.getBoolean("installed_inventory_qualified"))
        assertEquals(401, request("GET", "/v1/state", headers = headers).first)
        assertEquals(404, request("POST", "/v1/install", "{}", headers).first)
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
}
