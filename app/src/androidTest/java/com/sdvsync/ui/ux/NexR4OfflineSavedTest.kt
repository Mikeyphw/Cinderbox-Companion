package com.sdvsync.ui.ux

import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.mods.ModDataStore
import com.sdvsync.mods.api.NexusModSource
import com.sdvsync.ui.components.BottomTab
import java.io.IOException
import java.util.concurrent.atomic.AtomicInteger
import okhttp3.OkHttpClient
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.ExternalResource
import org.junit.rules.RuleChain
import org.junit.rules.TestRule
import org.junit.runner.RunWith
import org.koin.core.context.GlobalContext
import org.koin.core.context.loadKoinModules
import org.koin.core.context.unloadKoinModules
import org.koin.dsl.module

/** Real MainActivity, fake local Saved metadata, NO API key, NO network or downloads.
 *  Run only on the dedicated, data-cleared CI emulator, never a user phone.
 */
@RunWith(AndroidJUnit4::class)
class NexR4OfflineSavedTest {
    private companion object {
        const val MOD_NAME = "NEX-R4 Offline Saved Fixture"
        const val PREFS = "ux05_mod_bookmarks"
    }
    private val nexusRequests = AtomicInteger(0)
    private val blockedClient = OkHttpClient.Builder().addInterceptor {
        nexusRequests.incrementAndGet()
        throw IOException("NEX_R4_REFUSED_UNEXPECTED_NEXUS_REQUEST")
    }.build()
    private val overrideModule = module { single { NexusModSource(blockedClient, get()) } }
    private val restoreModule = module { single { NexusModSource(get(), get()) } }
    private val compose = createAndroidComposeRule<MainActivity>()
    private var loaded = false

    private val fixture = object : ExternalResource() {
        override fun before() {
            val ctx = InstrumentationRegistry.getInstrumentation().targetContext
            // Emulator identity and API level are strictly verified by the hosted runner.
            val store = GlobalContext.get().get<ModDataStore>()
            assertEquals("NEX_R4_REFUSED_EXISTING_NEXUS_KEY", null, store.getNexusApiKey())
            val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            assertEquals("NEX_R4_REFUSED_EXISTING_BOOKMARKS", null, prefs.getString("cards", null))
            val item = JSONObject().put("source", "nexus").put("id", "7001")
                .put("name", MOD_NAME).put("author", "Local fixture")
                .put("category", "Utilities").put("version", "1.2.3")
                .put("summary", "A saved description from device storage")
                .put("picture", "https://example.invalid/never-fetch.png")
            assertTrue("NEX_R4_REFUSED_PREF_WRITE", prefs.edit()
                .putString("cards", JSONArray().put(item).toString()).commit())
            loadKoinModules(overrideModule)
            loaded = true
        }

        override fun after() {
            try {
                if (loaded) {
                    unloadKoinModules(overrideModule)
                    loadKoinModules(restoreModule)
                }
            } finally {
                InstrumentationRegistry.getInstrumentation().targetContext
                    .getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove("cards").commit()
                loaded = false
            }
        }
    }
    @get:Rule val rules: TestRule = RuleChain.outerRule(fixture).around(compose)

    private fun capture(stage: String) {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue("100% font", ctx.resources.configuration.fontScale in 0.98f..1.02f)
        val image = checkNotNull(InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot())
        val valid = (image.width == 786 && image.height == 1704) ||
            (image.width == 720 && image.height == 1600)
        assertTrue("NEX_R4_REFUSED_WRONG_VIEWPORT", valid)
        ctx.openFileOutput("nex-r4-$stage-${image.width / 2}.png", Context.MODE_PRIVATE).use {
            assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, it))
        }
    }

    @Test fun offlineSavedDetailIsMetadataOnlyWithoutProviderTraffic() {
        compose.onNodeWithTag(BottomTab.MODS.testTag).performClick()
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasText("Saved"))
        compose.onNodeWithText("Saved").performClick()
        compose.onNodeWithTag("cinderbox.screen.mods")
            .performScrollToNode(hasText(MOD_NAME))
        compose.onNodeWithText(MOD_NAME).assertIsDisplayed()
        capture("saved-card")
        // Exactly one persisted bookmark; tapping must NOT route to provider detail.
        compose.onNodeWithTag("nex.r2.card").performClick()
        compose.onNodeWithTag("nex.r4.offline-saved-detail").assertIsDisplayed()
        compose.onNodeWithTag("nex.r4.offline-title").assertIsDisplayed()
        compose.onNodeWithText("Saved metadata only. Live details, files and downloads require Nexus access.")
            .assertIsDisplayed()
        capture("offline-sheet")
        assertEquals("NEX_R4_REFUSED_PROVIDER_CALL", 0, nexusRequests.get())
        compose.onNodeWithTag("nex.r4.offline-close").performClick()
        compose.onNodeWithTag("cinderbox.screen.mods").assertIsDisplayed()
        assertEquals("NEX_R4_REFUSED_PROVIDER_CALL_AFTER_CLOSE", 0, nexusRequests.get())
        println("NEX_R4_REAL_MAIN_ACTIVITY_SAVED_OFFLINE_PASS")
    }
}
