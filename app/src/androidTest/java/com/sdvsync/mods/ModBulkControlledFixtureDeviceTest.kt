package com.sdvsync.mods

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.nio.file.Files
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** Isolated app-cache fixtures only. Real game data and production writes are excluded. */
@RunWith(AndroidJUnit4::class)
class ModBulkControlledFixtureDeviceTest {
    private lateinit var root: File
    private lateinit var mods: File
    private lateinit var manager: ModFileManager

    @Before fun setup() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        root = Files.createTempDirectory(context.cacheDir.toPath(), "m25-r2c-").toFile()
        mods = File(root, "Mods").also { check(it.mkdir()) }
        manager = ModFileManager(context, ModManifestParser(), mods)
    }

    @After fun cleanup() { root.deleteRecursively() }

    private fun add(name: String, id: String): File = File(mods, name).also { folder ->
        check(folder.mkdir())
        File(folder, "manifest.json").writeText(
            """{"Name":"$name","Author":"Fixture","Version":"1.0.0","UniqueID":"$id"}""")
        File(folder, "config.json").writeBytes(byteArrayOf(0, 1, 2, 4, 16, 64, 127))
    }

    @Test fun reviewedDisableCommitsOneTransactionAndPreservesBytes() {
        val folder = add("Alpha", "fixture.alpha")
        val bytes = File(folder, "config.json").readBytes()
        val preview = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        assertTrue(preview.blockers.isEmpty())
        assertEquals(64, preview.filesystemWitness?.length)
        assertEquals(1, manager.commitIsolatedBulkFixture(preview))
        assertFalse(folder.exists())
        assertArrayEquals(bytes, File(mods, ".Alpha/config.json").readBytes())
    }

    @Test fun reviewedEnableCommitsExactlyOneDotToggle() {
        val folder = add(".Beta", "fixture.beta")
        val bytes = File(folder, "config.json").readBytes()
        val preview = manager.previewBulkWithWitness(setOf("fixture.beta"), true)
        assertEquals(1, manager.commitIsolatedBulkFixture(preview))
        assertFalse(folder.exists())
        assertArrayEquals(bytes, File(mods, "Beta/config.json").readBytes())
    }

    @Test fun staleSourceBytesRefuseBeforeAnyRename() {
        add("Alpha", "fixture.alpha")
        val preview = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        File(mods, "Alpha/config.json").appendText("changed after review")
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(preview) }.isFailure)
        assertTrue(File(mods, "Alpha").exists())
        assertFalse(File(mods, ".Alpha").exists())
    }

    @Test fun copiedApprovalObjectCannotCommit() {
        add("Alpha", "fixture.alpha")
        val preview = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(preview.copy()) }.isFailure)
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(preview) }.isFailure)
        assertTrue(File(mods, "Alpha").exists())
    }

    @Test fun replayAfterSuccessfulCommitIsRefused() {
        add("Alpha", "fixture.alpha")
        val preview = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        assertEquals(1, manager.commitIsolatedBulkFixture(preview))
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(preview) }.isFailure)
        assertTrue(File(mods, ".Alpha").isDirectory)
        assertFalse(File(mods, "Alpha").exists())
    }

    @Test fun outsideCacheRootIsNeverAuthorizedForBulkWrites() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val elsewhere = Files.createTempDirectory(context.filesDir.toPath(), "m25-r2c-refuse-").toFile()
        try {
            val outsideMods = File(elsewhere, "Mods").also { check(it.mkdir()) }
            val outsideManager = ModFileManager(context, ModManifestParser(), outsideMods)
            val folder = File(outsideMods, "Alpha").also { check(it.mkdir()) }
            File(folder, "manifest.json").writeText(
                """{"Name":"Alpha","Author":"Fixture","Version":"1.0.0","UniqueID":"fixture.alpha"}""")
            val preview = outsideManager.previewBulkWithWitness(setOf("fixture.alpha"), false)
            assertTrue(runCatching { outsideManager.commitIsolatedBulkFixture(preview) }.isFailure)
            assertTrue(folder.isDirectory)
            assertFalse(File(outsideMods, ".Alpha").exists())
        } finally { elsewhere.deleteRecursively() }
    }

    @Test fun destinationCollisionAddedAfterReviewRefusesCommit() {
        add("Alpha", "fixture.alpha")
        val preview = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        add(".Alpha", "fixture.other")
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(preview) }.isFailure)
        assertTrue(File(mods, "Alpha").isDirectory)
        assertTrue(File(mods, ".Alpha").isDirectory)
    }

    @Test fun blockedOrNoOpReviewNeverBecomesAnApproval() {
        add("Alpha", "fixture.alpha")
        val blocked = manager.previewBulkWithWitness(setOf("fixture.missing"), false)
        assertTrue(blocked.blockers.isNotEmpty())
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(blocked) }.isFailure)
        val noOp = manager.previewBulkWithWitness(setOf("fixture.alpha"), true)
        assertTrue(noOp.steps.isEmpty())
        assertTrue(runCatching { manager.commitIsolatedBulkFixture(noOp) }.isFailure)
        assertTrue(File(mods, "Alpha").isDirectory)
    }
}
