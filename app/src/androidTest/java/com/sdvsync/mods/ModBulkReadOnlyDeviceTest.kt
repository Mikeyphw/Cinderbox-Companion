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

/** API36-only fixture acceptance. Never opens or writes the real game Mods folder. */
@RunWith(AndroidJUnit4::class)
class ModBulkReadOnlyDeviceTest {
    private lateinit var root: File
    private lateinit var mods: File
    private lateinit var manager: ModFileManager

    @Before fun setup() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        root = Files.createTempDirectory(context.cacheDir.toPath(), "m25-r2b-verify-").toFile()
        mods = File(root, "Mods").also { check(it.mkdir()) }
        manager = ModFileManager(context, ModManifestParser(), mods)
    }

    @After fun cleanup() { root.deleteRecursively() }

    private fun add(name: String, id: String): File = File(mods, name).also { folder ->
        check(folder.mkdir())
        File(folder, "manifest.json").writeText(
            """{"Name":"$name","Author":"Fixture","Version":"1.0.0", "UniqueID":"$id"}""")
        File(folder, "config.json").writeBytes(byteArrayOf(0, 1, 2, 3, 42, 127))
    }

    @Test fun previewVerifiesSelectedBytesWithoutChangingModFolders() {
        val a = add("Alpha", "fixture.alpha")
        val b = add(".Beta", "fixture.beta")
        val originalA = File(a, "config.json").readBytes()
        val originalB = File(b, "config.json").readBytes()
        val preview = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        assertTrue(preview.blockers.isEmpty())
        assertEquals(1, preview.steps.size)
        assertEquals(64, preview.filesystemWitness?.length)
        assertEquals("Alpha", preview.steps.single().fromFolder)
        assertEquals(".Alpha", preview.steps.single().toFolder)
        assertTrue(a.isDirectory)
        assertTrue(b.isDirectory)
        assertFalse(File(mods, ".Alpha").exists())
        assertArrayEquals(originalA, File(a, "config.json").readBytes())
        assertArrayEquals(originalB, File(b, "config.json").readBytes())
    }

    @Test fun changedConfigBytesAlterPhysicalWitness() {
        add("Alpha", "fixture.alpha")
        val first = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        File(mods, "Alpha/config.json").appendText("mutated")
        val second = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        assertNotEquals(first.filesystemWitness, second.filesystemWitness)
        assertTrue(File(mods, "Alpha").exists())
        assertFalse(File(mods, ".Alpha").exists())
    }

    @Test fun missingOrCollisionSelectionNeverMovesAFile() {
        val folder = add("Alpha", "fixture.alpha")
        val missing = manager.previewBulkWithWitness(setOf("fixture.notinstalled"), false)
        assertTrue(missing.blockers.isNotEmpty())
        assertNull(missing.filesystemWitness)
        add(".Alpha", "fixture.other")
        val collision = manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        assertTrue(collision.blockers.isNotEmpty())
        assertNull(collision.filesystemWitness)
        assertTrue(folder.isDirectory)
        assertTrue(File(mods, ".Alpha").isDirectory)
    }

    @Test fun symlinkedRootEntryRefusesInspectionAndDoesNotFollowLink() {
        val folder = add("Alpha", "fixture.alpha")
        val outside = File(root, "outside").also { it.writeText("untouched") }
        Files.createSymbolicLink(File(mods, "linked").toPath(), outside.toPath())
        assertTrue(runCatching {
            manager.previewBulkWithWitness(setOf("fixture.alpha"), false)
        }.isFailure)
        assertEquals("untouched", outside.readText())
        assertTrue(folder.isDirectory)
    }
}
