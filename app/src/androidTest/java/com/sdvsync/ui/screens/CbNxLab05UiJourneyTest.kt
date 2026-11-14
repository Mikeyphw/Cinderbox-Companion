package com.sdvsync.ui.screens

import android.content.Context
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.BuildConfig
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.mods.NexusLab04SyntheticPolicy
import com.sdvsync.mods.NexusPairingBridge
import com.sdvsync.mods.NexusPairingInbox
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/**
 * LAB05 hosted API36 UI journeys. Runs ONLY against the isolated cbnxLab app.
 * Never loads a real Iceraven extension, real Nexus account or production Mods directory.
 * The runner records a receipt for each method rather than claiming physical acceptance.
 */
@RunWith(AndroidJUnit4::class)
class CbNxLab05UiJourneyTest {
    @get:Rule val rule = createComposeRule()
    private val context: Context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun mods(): File = File(CinderboxPaths.MODS_DIR)
    private fun journal(): File = File(context.filesDir.canonicalFile,
        "cbnx06-lab04-synthetic-transaction.json")

    @Before fun labOnly() {
        assertTrue("LAB05_DEBUG_BUILD_REFUSED", BuildConfig.CBNX_LAB)
        assertEquals("com.sdvsync.cbnx06lab", context.packageName)
        CinderboxLabBoundary.initialize(context)
        CinderboxLabBoundary.requireModsRoot(mods())
        NexusPairingBridge.stop()
    }
    @After fun closeBridge() { NexusPairingBridge.stop() }

    private fun showPanel() {
        rule.setContent {
            MaterialTheme {
                Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
                    NexusPairingPanel()
                }
            }
        }
        rule.waitForIdle()
    }

    @Test fun unpairedConsentRemainsDisabledAfterWindowStart() {
        showPanel()
        rule.onNodeWithTag("cbnx06.lab.pairing-status").assertExists()
        rule.onNodeWithTag("cbnx03b.pairing.allow-handoff").performScrollTo().assertIsNotEnabled()
        rule.onNodeWithTag("cbnx03.pairing.start").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx03.pairing.code").assertExists()
        rule.onNodeWithTag("cbnx03b.pairing.allow-handoff").performScrollTo().assertIsNotEnabled()
        assertFalse(NexusPairingBridge.snapshot().handoffEnabled)
        rule.onNodeWithTag("cbnx03.pairing.stop").performScrollTo().performClick()
        assertFalse(NexusPairingBridge.snapshot().listening)
    }

    @Test fun cancelSyntheticInstallDoesNotWriteModsOrJournal() {
        // This hosted emulator must start with a fresh LAB data set.
        assertFalse(journal().exists())
        assertTrue(mods().listFiles()?.isEmpty() == true)
        showPanel()
        rule.onNodeWithTag("cbnx06.lab04.request-install").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx06.lab04.confirm-action").assertExists()
        rule.onNodeWithTag("cbnx06.lab04.cancel-action").performClick()
        rule.onNodeWithTag("cbnx06.lab04.confirm-action").assertDoesNotExist()
        assertFalse(journal().exists())
        assertTrue(mods().listFiles()?.isEmpty() == true)
    }

    @Test fun exactFileCancelKeepsRequestPendingWithoutBrowserLaunch() {
        assertTrue(NexusPairingInbox.initializeForLocalPairing(context))
        val id = "LAB05_" + UUID.randomUUID().toString().replace("-", "")
        val file = (900000000L + java.security.SecureRandom().nextInt(90000000)).toString()
        val admitted = NexusPairingInbox.admit(context, id, "995000001", file)
        assertEquals("pending_user_action", admitted.state)
        try {
            showPanel()
            rule.onNodeWithTag("cbnx03b.handoff.open-exact").performScrollTo().performClick()
            rule.onNodeWithTag("cbnx06.lab03c.confirm-open").assertExists()
            rule.onNodeWithTag("cbnx06.lab03c.cancel-open").performClick()
            rule.onNodeWithTag("cbnx06.lab03c.confirm-open").assertDoesNotExist()
            assertTrue(NexusPairingInbox.list(context).any { it.id == id && it.status == "PENDING" })
            assertFalse(journal().exists())
        } finally {
            assertTrue(NexusPairingInbox.resolve(context, id, "DISMISSED"))
        }
    }

    @Test fun userConfirmedSyntheticInstallAndRollbackRestoresEmptyLabRoot() {
        assertFalse(journal().exists())
        assertTrue(mods().listFiles()?.isEmpty() == true)
        showPanel()
        rule.onNodeWithTag("cbnx06.lab04.request-install").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx06.lab04.confirm-action").performClick()
        rule.waitUntil(90000) {
            journal().isFile && runCatching {
                JSONObject(journal().readText()).optString("state") == "INSTALLED"
            }.getOrDefault(false)
        }
        val folder = File(mods(), NexusLab04SyntheticPolicy.FOLDER)
        assertTrue(folder.isDirectory)
        assertTrue(File(folder, "manifest.json").isFile)
        rule.onNodeWithTag("cbnx06.lab04.action-feedback").assertExists()
        rule.onNodeWithTag("cbnx06.lab04.request-rollback").performScrollTo().performClick()
        rule.onNodeWithTag("cbnx06.lab04.confirm-action").performClick()
        rule.waitUntil(90000) {
            journal().isFile && runCatching {
                JSONObject(journal().readText()).optString("state") == "ROLLED_BACK"
            }.getOrDefault(false)
        }
        assertTrue(mods().listFiles()?.isEmpty() == true)
        rule.onNodeWithTag("cbnx06.lab04.action-feedback").assertExists()
        assertFalse(NexusPairingBridge.snapshot().handoffEnabled)
    }
}
