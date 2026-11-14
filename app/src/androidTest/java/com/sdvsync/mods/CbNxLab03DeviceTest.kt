package com.sdvsync.mods

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.BuildConfig
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.cinderbox.CinderboxPaths
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.InetSocketAddress
import java.net.Socket
import java.nio.charset.StandardCharsets
import java.util.UUID

/** Runs ONLY against :app:cbnxLab on an API36 emulator; no personal files or live Nexus. */
@RunWith(AndroidJUnit4::class)
class CbNxLab03DeviceTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    @After fun stopBridge() { NexusPairingBridge.stop() }

    private fun request(method: String, path: String, body: String = "",
                        auth: String? = null, nonce: String? = null): Pair<Int, JSONObject> {
        Socket().use { socket ->
            socket.connect(InetSocketAddress("127.0.0.1", 38472), 5000)
            socket.soTimeout = 8000
            val payload = body.toByteArray(StandardCharsets.UTF_8)
            val head = buildString {
                append("$method $path HTTP/1.1\r\nHost: 127.0.0.1:38472\r\n")
                if (method == "POST") append("Content-Type: application/json\r\nContent-Length: ${payload.size}\r\n")
                if (auth != null) append("Authorization: Bearer $auth\r\n")
                if (nonce != null) append("X-CBNX-Nonce: $nonce\r\n")
                append("Connection: close\r\n\r\n")
            }
            socket.getOutputStream().write(head.toByteArray(StandardCharsets.US_ASCII) + payload)
            socket.getOutputStream().flush()
            val input = BufferedInputStream(socket.getInputStream())
            val headers = ByteArrayOutputStream()
            while (headers.size() < 8192) {
                val b = input.read(); require(b >= 0) { "LAB03_TRUNCATED_HTTP_HEADERS" }
                headers.write(b)
                if (headers.toByteArray().takeLast(4) == listOf(13, 10, 13, 10).map { it.toByte() }) break
            }
            require(headers.size() < 8192) { "LAB03_OVERSIZED_HEADERS" }
            val lines = headers.toString(StandardCharsets.US_ASCII.name()).split("\r\n")
            val status = lines.first().split(' ')[1].toInt()
            val sizes = lines.filter { it.startsWith("Content-Length:", ignoreCase = true) }
            require(sizes.size == 1) { "LAB03_INVALID_LENGTH_HEADERS" }
            val length = sizes.single().substringAfter(':').trim().toInt()
            require(length in 0..65536) { "LAB03_UNBOUNDED_RESPONSE" }
            val bytes = ByteArray(length)
            var total = 0
            while (total < length) {
                val n = input.read(bytes, total, length - total)
                require(n > 0) { "LAB03_TRUNCATED_BODY" }; total += n
            }
            return status to JSONObject(String(bytes, StandardCharsets.UTF_8))
        }
    }

    @Test fun syntheticArchivePreviewDoesNotModifyLabMods() {
        assertTrue(BuildConfig.CBNX_LAB)
        assertEquals("com.sdvsync.cbnx06lab", context.packageName)
        val mods = File(CinderboxPaths.MODS_DIR)
        CinderboxLabBoundary.requireModsRoot(mods)
        val before = mods.listFiles()?.map { it.name to it.length() }?.sortedBy { it.first }
        val result = NexusLab03Evidence.previewSynthetic(context)
        val after = mods.listFiles()?.map { it.name to it.length() }?.sortedBy { it.first }
        assertEquals(before, after)
        assertEquals(64, result.archiveSha256.length)
        assertEquals(1, result.proposedChanges)
        assertTrue(result.archiveVerified)
        try {
            CinderboxLabBoundary.requirePrivate(File("/storage/emulated/0/StardewValley/desktop/Mods"))
            fail("LAB03_REAL_ROOT_ACCEPTED")
        } catch (_: IllegalArgumentException) { /* expected private-root refusal */ }
    }

    @Test fun labPairingRequiresConsentAndRecordsOnlyExactInboxRequest() {
        assertTrue(BuildConfig.CBNX_LAB)
        assertEquals(38471, NexusPairingBridge.PORT)
        assertEquals(38472, NexusPairingBridge.ACTIVE_PORT)
        NexusPairingBridge.stop()
        val initial = NexusPairingBridge.start(context)
        val code = requireNotNull(initial.code)
        assertEquals(9, code.length)
        val hello = request("GET", "/v1/hello")
        assertEquals(200, hello.first)
        val handshake = JSONObject().put("code", code)
            .put("challenge", hello.second.getString("challenge"))
        val paired = request("POST", "/v1/pair", handshake.toString())
        assertEquals(200, paired.first)
        val token = paired.second.getString("token")
        val id = "LAB03_" + UUID.randomUUID().toString().replace("-", "")
        val modId = "995000001"
        val fileId = ((100000000..999999999).random()).toString()
        val body = JSONObject().put("mod_id", modId).put("file_id", fileId)
            .put("request_id", id).toString()
        fun nonce() = UUID.randomUUID().toString().replace("-", "")
        val refused = request("POST", "/v1/handoff", body, token, nonce())
        assertEquals(403, refused.first)
        NexusPairingBridge.setHandoffEnabled(true)
        val accepted = request("POST", "/v1/handoff", body, token, nonce())
        assertEquals(202, accepted.first)
        assertEquals(false, accepted.second.getBoolean("download_started"))
        assertEquals(false, accepted.second.getBoolean("archive_staged"))
        assertEquals(false, accepted.second.getBoolean("installed"))
        assertEquals(id, accepted.second.getString("request_id"))
        assertTrue(NexusPairingInbox.list(context).any {
            it.id == id && it.modId == modId && it.fileId == fileId && it.status == "PENDING"
        })
        val replay = request("POST", "/v1/handoff", body, token, nonce())
        assertEquals(202, replay.first)
        assertEquals("already_seen", replay.second.getString("status"))
        assertTrue(NexusPairingInbox.resolve(context, id, "DISMISSED"))
        val revoked = request("POST", "/v1/revoke", "{}", token, nonce())
        assertEquals(200, revoked.first)
    }
}
