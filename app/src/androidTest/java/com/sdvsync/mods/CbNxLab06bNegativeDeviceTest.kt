package com.sdvsync.mods

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.BuildConfig
import com.sdvsync.cinderbox.CinderboxLabBoundary
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.mods.models.InstallResult
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * LAB06B: destructive tests confined to a disposable hosted API36 emulator's
 * isolated com.sdvsync.cbnx06lab private tree. No production roots, Nexus,
 * paired browser, privileged commands or release-side changes.
 * Each test is launched separately after the runner clears ONLY the LAB app.
 */
@RunWith(AndroidJUnit4::class)
class CbNxLab06bNegativeDeviceTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun mods() = File(CinderboxPaths.MODS_DIR)
    private fun journal() = File(context.filesDir.canonicalFile, "cbnx06-lab04-synthetic-transaction.json")
    private fun stageDir() = File(context.filesDir.canonicalFile, "cbnx06-lab03d-staging")
    private fun assertPrivateAndEmpty() {
        CinderboxLabBoundary.requireModsRoot(mods())
        assertTrue("LAB06B_MODS_NOT_EMPTY", mods().listFiles()?.isEmpty() == true)
    }
    private fun refuse(block: () -> Unit) {
        try {
            block()
            fail("LAB06B_EXPECTED_REFUSAL")
        } catch (e: IllegalStateException) { /* expected fail-closed guard */ }
        catch (e: IllegalArgumentException) { /* expected fail-closed guard */ }
    }
    @Before fun isolatedAndClean() {
        assertTrue("LAB06B_NOT_ISOLATED_VARIANT", BuildConfig.CBNX_LAB)
        assertEquals("com.sdvsync.cbnx06lab", BuildConfig.APPLICATION_ID)
        assertEquals("com.sdvsync.cbnx06lab", context.packageName)
        CinderboxLabBoundary.initialize(context)
        assertPrivateAndEmpty()
        assertFalse("LAB06B_STALE_JOURNAL", journal().exists())
        assertFalse("LAB06B_PRODUCTION_PACKAGE", context.packageName == "com.sdvsync")
    }

    @Test fun changedArchiveBytesCannotReachMods() {
        NexusLab03DArchiveStage.stageSynthetic(context)
        val zip = File(stageDir(), "lab03-synthetic.zip")
        CinderboxLabBoundary.requirePrivate(zip)
        assertTrue(zip.isFile)
        zip.appendBytes(byteArrayOf(1))
        refuse { NexusLab04SyntheticTransaction.installSynthetic(context) }
        assertPrivateAndEmpty()
        assertFalse(journal().exists())
    }

    @Test fun forgedNexusProvenanceCannotReachMods() {
        NexusLab03DArchiveStage.stageSynthetic(context)
        val file = File(stageDir(), "lab03d-staged-receipt.json")
        CinderboxLabBoundary.requirePrivate(file)
        val record = JSONObject(file.readText())
        record.put("nexus_file_provenance_verified", true)
        file.writeText(record.toString())
        refuse { NexusLab04SyntheticTransaction.installSynthetic(context) }
        assertPrivateAndEmpty()
        assertFalse(journal().exists())
    }

    @Test fun incorrectApprovalKeyCannotReachMods() {
        NexusLab03DArchiveStage.stageSynthetic(context)
        val zip = File(stageDir(), "lab03-synthetic.zip")
        CinderboxLabBoundary.requirePrivate(zip)
        val manager = ModFileManager(context, ModManifestParser())
        val result = manager.installFromZip(zip, "LAB06B_INVALID_APPROVAL_KEY")
        assertTrue("LAB06B_APPROVAL_BYPASSED", result is InstallResult.Error)
        assertPrivateAndEmpty()
        assertFalse(journal().exists())
    }

    @Test fun interruptedIntentRequiresManualReview() {
        val evidence = NexusLab03DArchiveStage.stageSynthetic(context)
        CinderboxLabBoundary.requirePrivate(journal())
        val intent = JSONObject()
            .put("schema", NexusLab04SyntheticPolicy.SCHEMA)
            .put("scope", NexusLab04SyntheticPolicy.SCOPE)
            .put("source_provenance", NexusLab04SyntheticPolicy.SOURCE)
            .put("archive_sha256", evidence.sha256)
            .put("target_folder", NexusLab04SyntheticPolicy.FOLDER)
            .put("state", "INSTALLING")
            .put("nexus_file_provenance_verified", false)
            .put("production_files_examined", false)
        journal().writeText(intent.toString())
        refuse { NexusLab04SyntheticTransaction.installSynthetic(context) }
        refuse { NexusLab04SyntheticTransaction.rollbackSynthetic(context) }
        assertPrivateAndEmpty()
        assertEquals("INSTALLING", JSONObject(journal().readText()).getString("state"))
    }

    @Test fun completedRollbackCannotReplayOrReinstall() {
        val installed = NexusLab04SyntheticTransaction.installSynthetic(context)
        assertEquals("INSTALLED", installed.state)
        val rolledBack = NexusLab04SyntheticTransaction.rollbackSynthetic(context)
        assertEquals("ROLLED_BACK", rolledBack.state)
        assertTrue(rolledBack.restoredEmptyRoot)
        assertPrivateAndEmpty()
        refuse { NexusLab04SyntheticTransaction.rollbackSynthetic(context) }
        refuse { NexusLab04SyntheticTransaction.installSynthetic(context) }
        assertEquals("ROLLED_BACK", JSONObject(journal().readText()).getString("state"))
        assertPrivateAndEmpty()
    }
}
