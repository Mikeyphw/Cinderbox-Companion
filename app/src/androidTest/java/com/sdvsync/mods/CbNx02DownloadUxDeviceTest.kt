package com.sdvsync.mods

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Isolated app-private fixtures only; never touches the real Mods directory or Nexus. */
@RunWith(AndroidJUnit4::class)
class CbNx02DownloadUxDeviceTest {
    @Test fun approvalCanBeDisabledAndRestored() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val previous = ModDownloadPreferences.requiresApproval(context)
        try {
            ModDownloadPreferences.setRequiresApproval(context, false)
            assertFalse(ModDownloadPreferences.requiresApproval(context))
            ModDownloadPreferences.setRequiresApproval(context, true)
            assertTrue(ModDownloadPreferences.requiresApproval(context))
        } finally {
            ModDownloadPreferences.setRequiresApproval(context, previous)
        }
    }

    @Test fun queuedReviewPreservesExactFileIdsAndPromotesNext() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val dir = File(context.cacheDir, "cbnx02-queue-${System.nanoTime()}")
        assertTrue(dir.mkdirs())
        try {
            val zip = File(dir, "fixture.zip")
            zip.writeText("synthetic fixture, not an installable ZIP")
            val queue = ModReviewQueue(dir)
            queue.enqueue(zip, "First", "nexus", "50535", "178239", "job-a")
            queue.enqueue(zip, "Second", "nexus", "50535", "190561", "job-b")
            assertEquals(2, queue.pendingCount())
            assertEquals("178239", queue.receipt().fileId)
            assertEquals("50535", queue.receipt().modId)
            assertEquals(64, queue.receipt().sha256.length)
            assertEquals("job-a", queue.receipt().jobId)
            queue.clear()
            assertEquals(1, queue.pendingCount())
            assertEquals("190561", queue.receipt().fileId)
            queue.clear()
            assertFalse(queue.hasPending())
        } finally {
            dir.deleteRecursively()
        }
    }

    @Test fun stagedArchiveChecksumRejectsTamperingWithoutInstalling() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val dir = File(context.cacheDir, "cbnx02-tamper-${System.nanoTime()}")
        assertTrue(dir.mkdirs())
        try {
            val input = File(dir, "fixture.txt").apply { writeText("known fake bytes") }
            val queue = ModReviewQueue(dir)
            queue.enqueue(input, "Synthetic", "nexus", "50535", "178239", "test-job")
            assertNotNull(queue.archive())
            File(dir, "mod-review-pending.zip").appendText("!tampered!")
            assertNull(queue.archive())
            assertTrue(queue.hasPending()) // remain visible so it can be discarded
        } finally { dir.deleteRecursively() }
    }

    @Test fun terminalInstallIsNotOverwrittenByServiceCancellation() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val journal = ModDownloadJournal(context)
        val id = journal.create("Synthetic completion", "nexus", "50535", "178239")
        try {
            journal.update(id, "INSTALLED", detail = "Installed successfully")
            journal.cancelIfActive(id, "Late service destruction")
            assertEquals("INSTALLED", journal.list().first { it.id == id }.status)
        } finally { journal.update(id, "DISCARDED", detail = "Test cleanup") }
    }

    @Test fun journalRetainsFileIdentityWithoutBearerUrl() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val journal = ModDownloadJournal(context)
        val id = journal.create("Synthetic Mod", "nexus", "50535", "178239")
        try {
            journal.update(id, "DOWNLOADING", 1024, 4096, "Downloading archive")
            val job = journal.list().first { it.id == id }
            assertEquals("178239", job.fileId)
            assertEquals(1024L, job.received)
            assertEquals("DOWNLOADING", job.status)
        } finally {
            journal.update(id, "DISCARDED", detail = "Synthetic test finished")
        }
    }
}
