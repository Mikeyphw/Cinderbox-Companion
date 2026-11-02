package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.local.PlatformStoragePaths
import com.sdvsync.local.StoragePreflight
import java.io.File
import java.nio.file.Files
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** App-cache-only, no network, no Steam credentials, no game/save paths. */
@RunWith(AndroidJUnit4::class)
class PlatformStorageAliasDeviceTest {
    @Test fun rawAppCachePathIsAcceptedAndChildLinksAreRejected() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val cache = context.cacheDir.absoluteFile
        // Inspect the actual Android-managed external-files alias in the app's
        // own mount namespace. Skip only if external storage is not mounted.
        context.getExternalFilesDir(null)?.let { external ->
            val result = PlatformStoragePaths.inspect(external.absoluteFile)
            assertTrue("External Android path refused: ${result.reason}", result.safe)
        }
        val root = File(cache, "storage-alias-${UUID.randomUUID()}")
        assertTrue(root.mkdir())
        try {
            assertTrue(PlatformStoragePaths.inspect(root).safe)
            assertTrue(StoragePreflight.check(File(root, "new-game")).writable)
            val linked = File(root, "user-link")
            Files.createSymbolicLink(linked.toPath(), root.toPath())
            assertFalse(PlatformStoragePaths.inspect(File(linked, "new-game")).safe)
            assertFalse(StoragePreflight.check(File(linked, "new-game")).writable)
        } finally {
            // Unlink the synthetic cycle before recursive cleanup.
            Files.deleteIfExists(File(root, "user-link").toPath())
            assertEquals(cache.canonicalFile, root.canonicalFile.parentFile)
            assertTrue(root.deleteRecursively())
        }
    }
}
