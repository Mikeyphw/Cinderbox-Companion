package com.sdvsync.local

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class StoragePlannerTest {
    @Test fun userEstimateValidationAndUnknownAreHonest() {
        assertTrue(StoragePlanner.parseGiB("") == null)
        assertEquals(1073741824L, StoragePlanner.parseGiB("1"))
        assertTrue(runCatching { StoragePlanner.parseGiB("501") }.isFailure)
        assertTrue(runCatching { StoragePlanner.parseGiB("nonsense") }.isFailure)
    }
    @Test fun capacityEstimateIsConservative() {
        val dir = Files.createTempDirectory("m11-plan-").toFile()
        try {
            val unknown = StoragePlanner.plan(dir)
            assertTrue(unknown.payloadBytes == null)
            assertTrue(unknown.sufficient == null)
            val tooBig = StoragePlanner.plan(dir, Long.MAX_VALUE)
            assertFalse(tooBig.sufficient ?: true)
            val enough = StoragePlanner.plan(dir, 1L, 0)
            assertEquals(true, enough.sufficient)
            assertEquals(1L, enough.requiredBytes)
        } finally { dir.deleteRecursively() }
    }
    @Test fun missingAndSymlinkDestinationsFailClosed() {
        val dir = Files.createTempDirectory("m11-plan-").toFile()
        try {
            val file = File(dir, "file").apply { writeText("x") }
            assertEquals(false, StoragePlanner.plan(file, 10).sufficient)
            val link = File(dir, "link")
            Files.createSymbolicLink(link.toPath(), dir.toPath())
            assertEquals(false, StoragePlanner.plan(File(link, "child"), 10).sufficient)
        } finally { dir.deleteRecursively() }
    }
    @Test fun copySizeUsesExactSourceBytesAndRejectsLinks() {
        val dir = Files.createTempDirectory("m11-copy-").toFile()
        try {
            val src = File(dir, "source").apply { writeBytes(ByteArray(19)) }
            val result = StoragePlanner.copyPlan(File(dir, "dest"), listOf(src))
            assertEquals(19L, result.payloadBytes)
            val link = File(dir, "shortcut")
            Files.createSymbolicLink(link.toPath(), src.toPath())
            assertTrue(runCatching {
                StoragePlanner.copyPlan(File(dir, "dest"), listOf(link))
            }.isFailure)
        } finally { dir.deleteRecursively() }
    }
}
