package com.sdvsync.mods

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class ModSafetyTest {
    private fun withDirectories(test: (File, File, ModSafety) -> Unit) {
        val root = Files.createTempDirectory("m5-mod-test-").toFile()
        val state = File(root, "private").apply { mkdir() }
        val mods = File(root, "mods").apply { mkdir() }
        try { test(state, mods, ModSafety(state, mods)) } finally { root.deleteRecursively() }
    }

    @Test fun `retained snapshot survives source removal and restores it`() = withDirectories { _, mods, safety ->
        val target = File(mods, "TestMod").apply { mkdir() }
        File(target, "manifest.json").writeText("before")
        val backup = requireNotNull(safety.snapshot(target))
        assertEquals(1, safety.list().size)
        assertTrue(target.deleteRecursively())
        assertTrue(safety.restore(backup.id))
        assertEquals("before", File(target, "manifest.json").readText())
    }

    @Test fun `recovery restores missing mod after interrupted operation`() = withDirectories { _, mods, safety ->
        val target = File(mods, "TestMod").apply { mkdir() }
        File(target, "manifest.json").writeText("original")
        val backup = requireNotNull(safety.snapshot(target))
        safety.begin("TestMod", backup, "install")
        assertTrue(target.deleteRecursively())
        assertTrue(safety.recover())
        assertEquals("original", File(target, "manifest.json").readText())
        assertTrue(safety.recover())
    }

    @Test fun `invalid journal does not overwrite unknown data`() = withDirectories { state, mods, safety ->
        safety.begin("TestMod", null, "install")
        assertFalse(safety.recover())
        assertTrue(File(state, "mod-operation.properties").exists())
        assertFalse(File(mods, "TestMod").exists())
    }

    @Test fun `unbacked journal cannot acknowledge an unknown existing mod`() = withDirectories { state, mods, safety ->
        safety.begin("TestMod", null, "install")
        val unexpected = File(mods, "TestMod").apply { mkdir() }
        File(unexpected, "manifest.json").writeText("someone else's files")
        assertFalse(safety.recover())
        assertEquals("someone else's files", File(unexpected, "manifest.json").readText())
        assertTrue(File(state, "mod-operation.properties").exists())
    }

    @Test fun `journal cannot use another mod snapshot`() = withDirectories { state, mods, safety ->
        val other = File(mods, "OtherMod").apply { mkdir() }
        File(other, "manifest.json").writeText("unrelated")
        val wrong = requireNotNull(safety.snapshot(other))
        safety.begin("TestMod", wrong, "install")
        assertFalse(safety.recover())
        assertFalse(File(mods, "TestMod").exists())
        assertTrue(File(state, "mod-operation.properties").exists())
    }

    @Test fun `matching snapshot can finalize a promoted replacement`() = withDirectories { state, mods, safety ->
        val target = File(mods, "TestMod").apply { mkdir() }
        File(target, "manifest.json").writeText("old")
        val backup = requireNotNull(safety.snapshot(target))
        safety.begin("TestMod", backup, "install")
        File(target, "manifest.json").writeText("new")
        assertTrue(safety.recover())
        assertEquals("new", File(target, "manifest.json").readText())
        assertFalse(File(state, "mod-operation.properties").exists())
    }

    @Test fun `review queue survives reopening and prevents replacement`() = withDirectories { state, _, _ ->
        val input = File(state, "test.zip").apply { writeText("fake zip archive") }
        val queue = ModReviewQueue(state)
        queue.enqueue(input, "TestMod", "local", "")
        assertTrue(ModReviewQueue(state).hasPending())
        assertEquals("TestMod", ModReviewQueue(state).description())
        assertThrows(IllegalStateException::class.java) { queue.enqueue(input, "second", "local", "") }
        queue.clear()
        assertFalse(queue.hasPending())
    }

    @Test fun `symlinked mod is never backed up`() = withDirectories { state, mods, safety ->
        val elsewhere = File(state, "secret").apply { mkdir() }
        val link = File(mods, "linked")
        Files.createSymbolicLink(link.toPath(), elsewhere.toPath())
        assertThrows(IllegalArgumentException::class.java) { safety.snapshot(link) }
    }
}
