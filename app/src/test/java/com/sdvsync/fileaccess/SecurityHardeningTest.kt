package com.sdvsync.fileaccess

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SecurityHardeningTest {
    @Test fun shellQuotesUntrustedPathsAsSingleArguments() {
        val payload = "farm's save; touch /tmp/should-not-run $(echo BAD)\nsecond line"
        val p = ProcessBuilder("sh", "-c", "printf %s ${RootShell.quote(payload)}").start()
        val output = p.inputStream.bufferedReader().readText()
        assertEquals(0, p.waitFor())
        assertEquals(payload, output)
    }

    @Test fun canonicalScopingRejectsSiblingAndTraversal() {
        val parent = Files.createTempDirectory("sdvsync-security-").toFile()
        try {
            val root = File(parent, "Saves").apply { mkdirs() }
            assertTrue(PrivilegedSavePaths.isWithin(root, root))
            assertTrue(PrivilegedSavePaths.isWithin(root, File(root, "My Farm_123/SaveGameInfo")))
            assertFalse(PrivilegedSavePaths.isWithin(root, File(parent, "Saves-evil/farm")))
            assertFalse(PrivilegedSavePaths.isWithin(root, File(root, "../outside")))
            val outside = File(parent, "outside").apply { mkdirs() }
            val link = File(root, "escape").toPath()
            Files.createSymbolicLink(link, outside.toPath())
            assertFalse(PrivilegedSavePaths.isWithin(root, File(root, "escape/secret")))
        } finally {
            parent.deleteRecursively()
        }
    }
}
