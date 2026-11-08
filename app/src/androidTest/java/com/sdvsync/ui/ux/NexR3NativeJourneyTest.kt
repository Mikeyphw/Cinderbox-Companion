package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.test.espresso.Espresso
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.mods.ModDataStore
import com.sdvsync.mods.api.NexusModSource
import com.sdvsync.ui.components.BottomTab
import java.io.IOException
import java.util.Collections
import java.util.concurrent.atomic.AtomicReference
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import okio.Buffer
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.ExternalResource
import org.junit.rules.RuleChain
import org.junit.runner.RunWith
import org.junit.rules.TestRule
import org.koin.core.context.GlobalContext
import org.koin.core.context.loadKoinModules
import org.koin.core.context.unloadKoinModules
import org.koin.dsl.module

/** Real MainActivity + real route/ViewModel/provider parsing, but strictly synthetic HTTP responses.
 * NO real Nexus account, credentials, network, files, installation or device qualification.
 */
@RunWith(AndroidJUnit4::class)
class NexR3NativeJourneyTest {
    private companion object {
        const val FIXTURE_KEY = "NEX_R3_SYNTHETIC_NOT_A_REAL_NEXUS_KEY"
        const val MOD_NAME = "NEX-R3 Synthetic Mod"
        const val FILE_NAME = "nex-r3-fixture-primary.zip"
    }

    private enum class Mode { SUCCESS, AUTH_401, RATE_429, SERVER_503 }

    /** Intercepts ONLY Nexus API traffic; unexpected calls fail closed before a socket is opened. */
    private class OfflineNexusTransport : Interceptor {
        val mode = AtomicReference(Mode.SUCCESS)
        val offsets = Collections.synchronizedList(mutableListOf<Int>())
        val paths = Collections.synchronizedList(mutableListOf<String>())

        override fun intercept(chain: Interceptor.Chain): Response {
            val request = chain.request()
            val url = request.url
            if (url.host != "api.nexusmods.com" || url.scheme != "https") {
                throw IOException("NEX_R3_REFUSED_UNEXPECTED_HOST")
            }
            if (request.header("apikey") != FIXTURE_KEY) {
                throw IOException("NEX_R3_REFUSED_UNEXPECTED_KEY")
            }
            paths.add(request.method + " " + url.encodedPath)
            val status = when (mode.get()) {
                Mode.SUCCESS -> 200
                Mode.AUTH_401 -> 401
                Mode.RATE_429 -> 429
                Mode.SERVER_503 -> 503
            }
            if (status != 200) return result(request, status, "{}")
            return when {
                url.encodedPath == "/v2/graphql" && request.method == "POST" -> {
                    val buffer = Buffer()
                    request.body?.writeTo(buffer)
                    val payload = JSONObject(buffer.readUtf8())
                    val doc = payload.optString("query")
                    if (!doc.contains("modCategory") || !doc.contains("updatedAt"))
                        throw IOException("NEX_R3_REFUSED_UNEXPECTED_GRAPHQL_DOCUMENT")
                    val vars = payload.getJSONObject("variables")
                    val clauses = vars.getJSONObject("filter").getJSONArray("filter")
                    val gamePinned = (0 until clauses.length()).any { i ->
                        clauses.optJSONObject(i)?.optJSONObject("gameId")?.optString("value") == "1303"
                    }
                    if (!gamePinned) throw IOException("NEX_R3_REFUSED_UNPINNED_GAME")
                    val offset = vars.getInt("offset")
                    if (offset != 0 && offset != 50) throw IOException("NEX_R3_REFUSED_OFFSET")
                    offsets.add(offset)
                    val nodes = JSONArray()
                    val ids = if (offset == 0) 7001..7050 else 7051..7052
                    for (id in ids) {
                        nodes.put(JSONObject()
                            .put("modId", id)
                            .put("name", if (id == 7001) MOD_NAME else if (id == 7051)
                                "NEX-R3 Page Two" else "Synthetic Mod $id")
                            .put("author", "Fixture only")
                            .put("summary", "Metadata fixture; not a Nexus listing")
                            .put("version", "1.2.3")
                            .put("pictureUrl", JSONObject.NULL)
                            .put("modCategory", JSONObject().put("name", "Utilities"))
                            .put("endorsementCount", 32)
                            .put("modDownloadCount", 95)
                            .put("updatedAt", "2026-01-02T03:04:05Z"))
                    }
                    result(request, 200, JSONObject().put("data", JSONObject().put("mods",
                        JSONObject().put("nodes", nodes).put("totalCount", 52))).toString())
                }
                url.encodedPath == "/v1/games/stardewvalley/mods/7001.json" && request.method == "GET" -> {
                    result(request, 200, JSONObject()
                        .put("mod_id", 7001).put("name", MOD_NAME)
                        .put("author", "Fixture only")
                        .put("summary", "Read-only synthetic detail metadata")
                        .put("description", "Read-only synthetic detail metadata")
                        .put("category_name", "Utilities")
                        .put("picture_url", JSONObject.NULL)
                        .put("version", "1.2.3").put("endorsement_count", 32)
                        .put("mod_downloads", 95).put("updated_timestamp", 1767323045).toString())
                }
                url.encodedPath == "/v1/games/stardewvalley/mods/7001/files.json" && request.method == "GET" -> {
                    val files = JSONArray().put(JSONObject()
                        .put("file_id", 8001).put("file_name", FILE_NAME)
                        .put("version", "1.2.3").put("size_in_bytes", 8192)
                        .put("is_primary", true).put("category_name", "MAIN")
                        .put("description", "Synthetic file, no download allowed")
                        .put("uploaded_timestamp", 1767323045))
                    result(request, 200, JSONObject().put("files", files).toString())
                }
                else -> throw IOException("NEX_R3_REFUSED_UNEXPECTED_API_PATH")
            }
        }

        private fun result(request: okhttp3.Request, code: Int, json: String): Response =
            Response.Builder().request(request).protocol(Protocol.HTTP_1_1)
                .code(code).message("Synthetic fixture only")
                .body(json.toResponseBody("application/json".toMediaType())).build()
    }

    private val transport = OfflineNexusTransport()
    private val offlineClient = OkHttpClient.Builder().addInterceptor(transport).build()
    private val overrideModule = module { single { NexusModSource(offlineClient, get()) } }
    // Restore just the original Nexus source definition between test methods.
    private val restoreModule = module { single { NexusModSource(get(), get()) } }
    private val compose = createAndroidComposeRule<MainActivity>()
    private var store: ModDataStore? = null
    private var wasLoaded = false

    /** This rule runs BEFORE MainActivity is launched by the Compose rule. */
    private val fixture = object : ExternalResource() {
        override fun before() {
            val dataStore = GlobalContext.get().get<ModDataStore>()
            // This lane is only for a fresh hosted emulator, never real user accounts.
            assertEquals("NEX_R3_REFUSED_NON_EPHEMERAL_DEVICE", null, dataStore.getNexusApiKey())
            store = dataStore
            dataStore.setNexusApiKey(FIXTURE_KEY)
            assertEquals(FIXTURE_KEY, dataStore.getNexusApiKey())
            loadKoinModules(overrideModule)
            wasLoaded = true
        }

        override fun after() {
            try {
                if (wasLoaded) {
                    unloadKoinModules(overrideModule)
                    loadKoinModules(restoreModule)
                }
            } finally {
                store?.setNexusApiKey(null)
                store = null
                wasLoaded = false
            }
        }
    }

    @get:Rule val rules: TestRule = RuleChain.outerRule(fixture).around(compose)

    private fun visible(tag: String) {
        val end = SystemClock.uptimeMillis() + 35000L
        do {
            compose.waitForIdle()
            try { compose.onNodeWithTag(tag).assertIsDisplayed(); return }
            catch (_: AssertionError) { SystemClock.sleep(150) }
        } while (SystemClock.uptimeMillis() < end)
        try {
            compose.onNodeWithTag(tag).assertIsDisplayed()
        } catch (failure: AssertionError) {
            throw AssertionError("NEX_R3_TAG_TIMEOUT:" + tag, failure)
        }
    }

    private fun textVisible(value: String) {
        // A real UI assertion, never a synthetic success. Surface the exact timed-out
        // condition instead of the original anonymous ComposeTimeoutException.
        try {
            compose.waitUntil(35000L) {
                compose.onAllNodesWithText(value).fetchSemanticsNodes().isNotEmpty()
            }
            compose.onNodeWithText(value).assertIsDisplayed()
        } catch (failure: Throwable) {
            val stage = when (value) {
                MOD_NAME -> "synthetic-mod-title"
                "NEX-R3 Page Two" -> "second-page-title"
                "Mod catalog unavailable" -> "catalog-error"
                "Nexus connection required" -> "no-api-key"
                else -> "unidentified"
            }
            throw AssertionError("NEX_R3_TEXT_TIMEOUT:" + stage +
                ":nexus_requests=" + transport.paths.size +
                ":page_offsets=" + transport.offsets.size, failure)
        }
    }

    private fun waitForPageOffset50() {
        try {
            compose.waitUntil(35000L) { transport.offsets.contains(50) }
        } catch (failure: Throwable) {
            throw AssertionError("NEX_R3_OFFSET_TIMEOUT:50" +
                ":nexus_requests=" + transport.paths.size, failure)
        }
    }

    private fun capture(label: String) {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue("100% default font only", ctx.resources.configuration.fontScale in 0.98f..1.02f)
        val bitmap = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        assertTrue("Only 360dp/393dp source-bound screen sizes",
            (bitmap.width == 720 && bitmap.height == 1600) ||
                (bitmap.width == 786 && bitmap.height == 1704))
        // Simple nonblank check; detailed PNG inventory validated host-side.
        val pixels = mutableSetOf<Int>()
        for (y in bitmap.height / 8 until bitmap.height * 7 / 8 step 27)
            for (x in bitmap.width / 8 until bitmap.width * 7 / 8 step 27)
                pixels.add(bitmap.getPixel(x, y) and 0xffffff)
        assertTrue("Refuse blank synthetic screenshot", pixels.size >= 8)
        val filename = "nex-r3-$label-${bitmap.width / 2}.png"
        ctx.openFileOutput(filename, Context.MODE_PRIVATE).use { output ->
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output))
        }
        println("NEX_R3_EPHEMERAL_SCREENSHOT:$filename")
    }

    private fun openMods() {
        visible(BottomTab.MODS.testTag)
        compose.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        visible("cinderbox.screen.mods")
    }

    private fun assertNoDownloadRequests() {
        assertFalse("No download-link requests", transport.paths.any { it.contains("download_link") })
        assertFalse("No external file transfer", transport.paths.any { it.contains("/download") })
    }

    @Test fun realMainActivityDiscoverPagingDetailReviewAndBack() {
        openMods()
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("nex.r2.card"))
        textVisible(MOD_NAME)
        capture("discover")

        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("cinderbox.mods.load-more"))
        compose.onNodeWithTag("cinderbox.mods.load-more").performClick()
        waitForPageOffset50()
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasTestTag("nex.r2.card"))
        // Page two is checked by provider-owned offset + rendered result, not by local filtering.
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(androidx.compose.ui.test.hasText("NEX-R3 Page Two"))
        textVisible("NEX-R3 Page Two")
        capture("page-two")

        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(androidx.compose.ui.test.hasText(MOD_NAME))
        compose.onNodeWithText(MOD_NAME).performClick()
        visible("cinderbox.screen.mod-detail")
        textVisible(MOD_NAME)
        capture("detail")
        compose.onNodeWithTag("cinderbox.mod-detail.list")
            .performScrollToNode(hasTestTag("cinderbox.mod-detail.files"))
        compose.onNodeWithTag("cinderbox.mod-detail.files").performClick()
        compose.onNodeWithText(FILE_NAME).performScrollTo().assertIsDisplayed()
        capture("file-review")
        assertNoDownloadRequests()

        Espresso.pressBack()
        visible("cinderbox.screen.mod-detail")
        compose.onNodeWithTag("cinderbox.mod-detail.list")
            .performScrollToNode(hasTestTag("cinderbox.mod-detail.back"))
        compose.onNodeWithTag("cinderbox.mod-detail.back").performClick()
        visible("cinderbox.screen.mods")
        capture("returned")
        assertNoDownloadRequests()
        assertTrue(transport.paths.any { it == "GET /v1/games/stardewvalley/mods/7001/files.json" })
        println("NEX_R3_REAL_NAVIGATION_SYNTHETIC_PROVIDER_PASS")
    }

    @Test fun authRateLimitAndServiceFailuresStayReadOnly() {
        transport.mode.set(Mode.AUTH_401)
        openMods()
        textVisible("Mod catalog unavailable")
        capture("auth-401")
        assertNoDownloadRequests()

        transport.mode.set(Mode.RATE_429)
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(androidx.compose.ui.test.hasText("New"))
        compose.onNodeWithText("New").performClick()
        textVisible("Mod catalog unavailable")
        capture("rate-429")

        transport.mode.set(Mode.SERVER_503)
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(androidx.compose.ui.test.hasText("Updated"))
        compose.onNodeWithText("Updated").performClick()
        textVisible("Mod catalog unavailable")
        capture("server-503")
        assertNoDownloadRequests()
        assertTrue(transport.paths.count { it == "POST /v2/graphql" } >= 3)
        println("NEX_R3_API_ERRORS_NO_FAKE_RESULTS_PASS")
    }

    @Test fun noNexusKeyKeepsLocalModsRouteAvailable() {
        store?.setNexusApiKey(null)
        openMods()
        textVisible("Nexus connection required")
        capture("no-key")
        assertTrue("No provider request permitted without key", transport.paths.isEmpty())
        println("NEX_R3_NO_KEY_LOCAL_ONLY_PASS")
    }
}
