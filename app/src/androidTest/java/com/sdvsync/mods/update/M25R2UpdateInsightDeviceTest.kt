package com.sdvsync.mods.update

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.mods.ModUpdateInsight
import com.sdvsync.mods.ModUpdateObservation
import com.sdvsync.mods.UpdateAssessment
import com.sdvsync.mods.api.SmapiUpdateResponseParser
import com.sdvsync.mods.api.SmapiUpdateChecker
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModManifest
import com.sdvsync.ui.components.M25UpdateStatusSummary
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Same disposable API36 emulator as R48; offline metadata fixtures only. */
@RunWith(AndroidJUnit4::class)
class M25R2UpdateInsightDeviceTest {
    @get:Rule val rule = createComposeRule()

    private fun installed(id: String, version: String = "1.0.0") = InstalledMod(
        manifest = ModManifest(name = id, author = "Fixture", version = version, uniqueID = id,
            description = "Synthetic R2 update fixture"),
        folderName = "fake", folderPath = "", enabled = true)

    @Test fun showsAllStatusesAtCompactFontScaleAndCapturesPreview() {
        val mods = listOf("A.New", "B.Current", "C.Ahead", "D.Unknown", "E.Incomparable")
            .map { installed(it) }
        val statuses = listOf(UpdateAssessment.NEWER, UpdateAssessment.CURRENT,
            UpdateAssessment.INSTALLED_AHEAD, UpdateAssessment.UNKNOWN,
            UpdateAssessment.UNCOMPARABLE)
        val evidence = mods.zip(statuses).associate { (mod, state) ->
            mod.manifest.uniqueID.lowercase(java.util.Locale.ROOT) to ModUpdateObservation(
                mod.manifest.uniqueID, mod.manifest.version, "2.0.0", state)
        }
        rule.setContent {
            MaterialTheme {
                Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
                    M25UpdateStatusSummary(mods, evidence, 10_000L, false, 11_000L)
                }
            }
        }
        rule.onNodeWithText("Update intelligence").assertIsDisplayed()
        rule.onNodeWithText("View mod statuses").performClick()
        rule.onNodeWithText("A.New — Update available").performScrollTo().assertIsDisplayed()
        rule.onNodeWithText("B.Current — Current version").performScrollTo().assertIsDisplayed()
        rule.onNodeWithText("C.Ahead — Installed version ahead").performScrollTo().assertIsDisplayed()
        val image = rule.onRoot().captureToImage().asAndroidBitmap()
        assertTrue(image.width >= 320 && image.height > 100)
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        ctx.openFileOutput("m25-r2-status-320dp-fs160.png", Context.MODE_PRIVATE).use {
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
    }

    @Test fun parserNeverClaimsCurrentForAbsentSuggestedVersion() {
        val mods = listOf(installed("Example.A"), installed("Example.B"))
        val data = JSONArray("""[{"id":"Example.A","suggestedUpdate":{"version":"1.0.0"}},
          {"id":"Example.B"}]""")
        val result = SmapiUpdateResponseParser.parse(mods, data, 1000L)
        assertEquals(UpdateAssessment.CURRENT, result.observations["example.a"]?.status)
        assertEquals(UpdateAssessment.UNKNOWN, result.observations["example.b"]?.status)
        assertTrue(result.updates.isEmpty())
    }

    @Test fun parserRejectsDuplicateAndUnknownRemoteIds() {
        val mods = listOf(installed("Example.A"))
        val dup = JSONArray("""[{"id":"Example.A"},{"id":"example.a"}]""")
        assertTrue(runCatching { SmapiUpdateResponseParser.parse(mods, dup, 1000L) }.isFailure)
        val unknown = JSONArray("""[{"id":"Not.Installed","suggestedUpdate":{"version":"9.0"}}]""")
        val result = SmapiUpdateResponseParser.parse(mods, unknown, 1000L)
        assertEquals(UpdateAssessment.UNKNOWN, result.observations["example.a"]?.status)
        assertTrue(result.updates.isEmpty())
    }

    @Test fun changelogAndFreshnessAreInertAndBounded() {
        val content = ModUpdateInsight.plainChangelog(
            "<script>alert('pw')</script><p>Fixed &amp; improved</p><a href='javascript:evil()'>Read</a>")!!
        assertTrue(content.contains("Fixed & improved"))
        assertFalse(content.contains("alert"))
        assertFalse(content.contains("javascript:"))
        assertNull(ModUpdateInsight.safeUpdateUrl("javascript:alert(1)"))
        assertNull(ModUpdateInsight.safeUpdateUrl("https://127.0.0.1/private"))
        assertEquals("Never checked", ModUpdateInsight.freshness(0L, 5000L))
        assertTrue(ModUpdateInsight.freshness(100L, 500L).startsWith("Checked"))
        assertTrue(ModUpdateInsight.freshness(100L, 100L + ModUpdateInsight.STALE_AFTER_MS + 1)
            .contains("expired"))
        // Synthetic interceptor: HTTP failures and malformed responses stay failures;
        // no real network, account, installed mod files or automatic install.
        for (status in listOf(503, 200)) {
            val client = OkHttpClient.Builder().addInterceptor { chain ->
                Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1)
                    .code(status).message("fixture")
                    .body((if (status == 503) "Unavailable" else "{bad json")
                        .toResponseBody()).build()
            }.build()
            assertTrue(runBlocking {
                runCatching { SmapiUpdateChecker(client).checkDetailed(listOf(installed("Example.A"))) }
                    .isFailure
            })
        }
    }
}
