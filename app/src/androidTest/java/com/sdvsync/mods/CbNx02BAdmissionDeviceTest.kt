package com.sdvsync.mods

import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.util.UUID
import java.util.concurrent.Executors
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Synthetic app-private journal fixtures. No Nexus network, game data or install calls. */
@RunWith(AndroidJUnit4::class)
class CbNx02BAdmissionDeviceTest {
    private class FixtureContext(base: Context) : ContextWrapper(base) {
        private val suffix = UUID.randomUUID().toString()
        override fun getSharedPreferences(name: String, mode: Int): SharedPreferences =
            super.getSharedPreferences("$name-hf02-$suffix", mode)
        override fun getFilesDir(): File = File(baseContext.cacheDir, "cbnx-hf02-$suffix").apply { mkdirs() }
    }
    private fun fixture() = FixtureContext(InstrumentationRegistry.getInstrumentation().targetContext)
    private fun journalForState(context: Context, status: String, file: String = "178239"): ModDownloadJournal {
        val journal = ModDownloadJournal(context)
        val id = journal.create("Offline synthetic", "nexus", "50535", file)
        if (status == "QUEUED") return journal
        assertTrue(journal.update(id, "DOWNLOADING"))
        if (status == "DOWNLOADING") return journal
        if (status == "PAUSED") { assertTrue(journal.update(id, "PAUSED")); return journal }
        assertTrue(journal.update(id, "VALIDATING"))
        if (status == "VALIDATING") return journal
        if (status == "INSTALLING") { assertTrue(journal.update(id, "INSTALLING")); return journal }
        assertTrue(journal.update(id, status))
        return journal
    }

    @Test fun allProtectedNexusStatesRefuseDuplicateAdmission() {
        for (status in listOf("QUEUED", "DOWNLOADING", "VALIDATING", "INSTALLING",
                "PAUSED", "VERIFY_REQUIRED", "REVIEW_REQUIRED", "BLOCKED")) {
            val context = fixture()
            val journal = journalForState(context, status)
            val before = journal.list().size
            val outcome = ModDownloadJournal(context).admit("Same identity", "nexus", "50535", "178239")
            assertFalse("status=$status", outcome.accepted)
            assertEquals("status=$status", before, journal.list().size)
        }
    }

    @Test fun differentExactFileCanAdmitWithoutModLevelLock() {
        val context = fixture()
        journalForState(context, "PAUSED")
        val next = ModDownloadJournal(context).admit("Another exact file", "nexus", "50535", "190561")
        assertTrue(next.userMessage, next.accepted)
        assertEquals("190561", ModDownloadJournal(context).list().first { it.id == next.jobId }.fileId)
    }

    @Test fun multipleJournalInstancesAdmitSameFileOnlyOnce() {
        val context = fixture()
        val executor = Executors.newFixedThreadPool(8)
        try {
            val futures = (1..24).map { executor.submit<ModDownloadAdmission> {
                ModDownloadJournal(context).admit("Concurrent", "nexus", "50535", "178239")
            } }
            assertEquals(1, futures.count { it.get().accepted })
            assertEquals(1, ModDownloadJournal(context).list().count { it.fileId == "178239" })
        } finally { executor.shutdownNow() }
    }

    @Test fun crashDuringInstallationIsVerifyOnlyEvenWithApprovalOff() {
        val context = fixture()
        val journal = journalForState(context, "INSTALLING")
        val id = journal.list().first().id
        journal.markInterrupted()
        assertEquals("VERIFY_REQUIRED", journal.list().first().status)
        assertFalse(journal.update(id, "INSTALLED"))
        assertFalse(journal.update(id, "DOWNLOADING"))
        assertFalse(journal.admit("Same file", "nexus", "50535", "178239").accepted)
    }

    @Test fun durableReviewReceiptBlocksAdmissionEvenWithoutJournalRow() {
        val context = fixture()
        val input = File(context.filesDir, "synthetic.txt").apply { writeText("not a real archive") }
        val review = ModReviewQueue(context.filesDir)
        review.enqueue(input, "Synthetic", "nexus", "50535", "178239", "lost-journal-row")
        val outcome = ModDownloadJournal(context).admit("Same exact file", "nexus", "50535", "178239")
        assertEquals("REVIEW_PENDING", outcome.reason)
        assertTrue(ModDownloadJournal(context).admit("Other exact file", "nexus", "50535", "190561").accepted)
    }

    @Test fun terminalAndUncertainStatesRejectLateWorkerWrites() {
        for (status in listOf("INSTALLED", "VERIFY_REQUIRED")) {
            val journal = journalForState(fixture(), "INSTALLING")
            val id = journal.list().first().id
            assertTrue(journal.update(id, status))
            journal.cancelIfActive(id, "Late service shutdown")
            journal.markJobInterrupted(id)
            assertFalse(journal.update(id, "DOWNLOADING"))
            assertEquals(status, journal.list().first().status)
        }
    }
}
