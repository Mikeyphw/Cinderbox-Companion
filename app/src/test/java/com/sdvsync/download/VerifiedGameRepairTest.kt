package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class VerifiedGameRepairTest {
    private data class Fixture(val root: File, val privateRoot: File, val src: File, val dest: File) {
        fun repair(verified: Boolean = true, before: (Int) -> Unit = {}) =
            VerifiedGameRepair(privateRoot, verifiedSource = { verified },
                hasPendingDownload = { false }, beforeReplace = before)
        fun file(dir: File, rel: String, text: String): File {
            val result = File(dir, rel)
            result.parentFile!!.mkdirs()
            result.writeText(text)
            return result
        }
    }
    private fun fixture(): Fixture {
        val root = Files.createTempDirectory("m10-game-repair-").toFile()
        val src = File(root, "verified").also { check(it.mkdir()) }
        val dest = File(root, "existing").also { check(it.mkdir()) }
        val privateDir = File(root, "private").also { check(it.mkdir()) }
        val f = Fixture(root, privateDir, src, dest)
        f.file(src, "Stardew Valley.dll", "verified-engine")
        f.file(dest, "Stardew Valley.dll", "original-engine")
        f.file(src, "Content/base.xnb", "verified-content")
        f.file(dest, "Content/base.xnb", "original-content")
        f.file(dest, "Mods/local-custom.dll", "custom content")
        return f
    }
    @Test fun repairsOnlyDiffsAndPreservesTargetExtras() {
        val f = fixture()
        try {
            val repair = f.repair(); val review = repair.preview(f.src, f.dest)
            assertEquals(2, review.changes.size)
            assertEquals(1, review.preservedFiles)
            assertTrue(review.changes.all { it.kind == "REPLACE" })
            assertEquals(2, repair.apply(review))
            assertEquals("verified-engine", File(f.dest, "Stardew Valley.dll").readText())
            assertEquals("custom content", File(f.dest, "Mods/local-custom.dll").readText())
            assertTrue(repair.recover())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun addsMissingFileWithoutRemovingExtras() {
        val f = fixture()
        try {
            f.file(f.src, "Content/new.xnb", "new-file")
            val repair = f.repair(); val plan = repair.preview(f.src, f.dest)
            assertTrue(plan.changes.any { it.path == "Content/new.xnb" && it.kind == "ADD" })
            assertEquals(3, repair.apply(plan))
            assertEquals("new-file", File(f.dest, "Content/new.xnb").readText())
            assertEquals("custom content", File(f.dest, "Mods/local-custom.dll").readText())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun staleDestinationReviewIsRejectedBeforeChanges() {
        val f = fixture()
        try {
            val repair = f.repair(); val plan = repair.preview(f.src, f.dest)
            f.file(f.dest, "Stardew Valley.dll", "changed-since-review")
            assertTrue(runCatching { repair.apply(plan) }.isFailure)
            assertEquals("changed-since-review", File(f.dest, "Stardew Valley.dll").readText())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun staleSourceReviewIsRejectedBeforeChanges() {
        val f = fixture()
        try {
            val repair = f.repair(); val plan = repair.preview(f.src, f.dest)
            f.file(f.src, "Content/base.xnb", "source-changed")
            assertTrue(runCatching { repair.apply(plan) }.isFailure)
            assertEquals("original-engine", File(f.dest, "Stardew Valley.dll").readText())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun unverifiedSourceCannotProducePreview() {
        val f = fixture()
        try { assertTrue(runCatching { f.repair(false).preview(f.src, f.dest) }.isFailure) }
        finally { f.root.deleteRecursively() }
    }
    @Test fun ordinaryMidBatchFailureRestoresOriginalFiles() {
        val f = fixture()
        try {
            val repair = f.repair(before = { if (it == 1) error("injected failure") })
            val review = repair.preview(f.src, f.dest)
            assertTrue(runCatching { repair.apply(review) }.isFailure)
            assertEquals("original-engine", File(f.dest, "Stardew Valley.dll").readText())
            assertEquals("original-content", File(f.dest, "Content/base.xnb").readText())
            assertTrue(repair.recover())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun processDeathBetweenWritesRollsBack() {
        val f = fixture()
        try {
            val repair = f.repair(before = { if (it == 1) throw AssertionError("process death") })
            val plan = repair.preview(f.src, f.dest)
            try { repair.apply(plan); fail("Injected death must escape") }
            catch (_: AssertionError) { }
            assertTrue(File(f.privateRoot, "m10-game-repair.properties").exists())
            assertTrue(f.repair().recover())
            assertEquals("original-engine", File(f.dest, "Stardew Valley.dll").readText())
            assertEquals("original-content", File(f.dest, "Content/base.xnb").readText())
            assertFalse(File(f.privateRoot, "m10-game-repair.properties").exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun externalEditsAfterCrashBlockAllRollback() {
        val f = fixture()
        try {
            val repair = f.repair(before = { if (it == 1) throw AssertionError("crash") })
            val plan = repair.preview(f.src, f.dest)
            try { repair.apply(plan) } catch (_: AssertionError) { }
            f.file(f.dest, "Stardew Valley.dll", "external edit")
            assertFalse(f.repair().recover())
            assertEquals("external edit", File(f.dest, "Stardew Valley.dll").readText())
            assertTrue(File(f.privateRoot, "m10-game-repair.properties").exists())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun symlinkOrNestedPathsCannotBeRepaired() {
        val f = fixture()
        try {
            val outside = File(f.root, "outside.txt").also { it.writeText("untouched") }
            Files.createSymbolicLink(File(f.dest, "Content/base.xnb").toPath().also { Files.delete(it) }, outside.toPath())
            assertTrue(runCatching { f.repair().preview(f.src, f.dest) }.isFailure)
            assertEquals("untouched", outside.readText())
            assertTrue(runCatching { f.repair().preview(f.src, f.src) }.isFailure)
        } finally { f.root.deleteRecursively() }
    }
    @Test fun destinationDirectoryCollisionIsRejectedBeforeChanges() {
        val f = fixture()
        try {
            File(f.src, "Content/extra.xnb").writeText("source")
            val conflict = File(f.dest, "Content/extra.xnb")
            assertTrue(conflict.mkdir())
            assertTrue(runCatching { f.repair().preview(f.src, f.dest) }.isFailure)
            assertTrue(conflict.isDirectory)
            assertEquals("original-engine", File(f.dest, "Stardew Valley.dll").readText())
        } finally { f.root.deleteRecursively() }
    }
    @Test fun missingGameAnchorRefusesUnrelatedTarget() {
        val f = fixture()
        try {
            File(f.dest, "Stardew Valley.dll").delete()
            File(f.dest, "Content").deleteRecursively()
            assertTrue(runCatching { f.repair().preview(f.src, f.dest) }.isFailure)
        } finally { f.root.deleteRecursively() }
    }
}
