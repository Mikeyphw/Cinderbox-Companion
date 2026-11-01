package com.sdvsync.local

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

/** Pure filesystem fixtures; test-only trust list is NOT configurable in production. */
class PlatformStoragePathsTest {
    @Test fun allowsOnlyAnExactTrustedPrefixAndRejectsUserControlledChildren() {
        val base = Files.createTempDirectory("cinderbox-storage-alias-").toFile()
        try {
            val actual = File(base, "real").apply { mkdir() }
            val alias = File(base, "platform-root")
            Files.createSymbolicLink(alias.toPath(), actual.toPath())
            val valid = File(alias, "game/new")
            assertFalse(Files.isSymbolicLink(valid.toPath()))
            assertFalse(PlatformStoragePaths.inspect(valid).safe)
            assertTrue(PlatformStoragePaths.inspect(valid, setOf(alias.path)).safe)
            val link = File(actual, "user-link")
            Files.createSymbolicLink(link.toPath(), actual.toPath())
            val malicious = PlatformStoragePaths.inspect(File(alias, "user-link/game"), setOf(alias.path))
            assertFalse(malicious.safe)
            assertEquals(File(alias, "user-link").path, malicious.component?.path)
            assertTrue(malicious.reason.contains(File(alias, "user-link").path))
            assertFalse(PlatformStoragePaths.inspect(File(alias, "../escape"), setOf(alias.path)).safe)
        } finally {
            Files.deleteIfExists(File(base, "real/user-link").toPath())
            Files.deleteIfExists(File(base, "platform-root").toPath())
            base.deleteRecursively()
        }
    }

    @Test fun directAndMissingOrdinaryFoldersAreSafeButForeignLinksFail() {
        val base = Files.createTempDirectory("cinderbox-direct-").toFile()
        try {
            assertTrue(PlatformStoragePaths.inspect(File(base, "new/game")).safe)
            assertTrue(StoragePreflight.check(File(base, "new/game")).writable)
            val external = File(base, "link")
            Files.createSymbolicLink(external.toPath(), base.toPath())
            assertFalse(StoragePreflight.check(File(external, "new/game")).writable)
        } finally {
            Files.deleteIfExists(File(base, "link").toPath())
            base.deleteRecursively()
        }
    }

    @Test fun danglingTrustedAliasIsNotAccepted() {
        val base = Files.createTempDirectory("cinderbox-dangling-").toFile()
        try {
            val alias = File(base, "platform-root")
            Files.createSymbolicLink(alias.toPath(), File(base, "missing-target").toPath())
            val result = PlatformStoragePaths.inspect(File(alias, "game"), setOf(alias.path))
            assertFalse(result.safe)
            assertTrue(result.reason.contains("Unavailable Android storage alias"))
        } finally { base.deleteRecursively() }
    }

    @Test fun absoluteOnlyAndDotDotNeverAllowed() {
        assertFalse(PlatformStoragePaths.inspect(File("relative")).safe)
        assertFalse(PlatformStoragePaths.inspect(File("/tmp/../tmp/target")).safe)
        assertFalse(PlatformStoragePaths.inspect(File("/tmp/\u0000bad")).safe)
    }
}
