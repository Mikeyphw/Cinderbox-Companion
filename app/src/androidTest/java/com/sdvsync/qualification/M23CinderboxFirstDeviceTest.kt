package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.local.M23CinderboxFirstPolicy
import java.io.File
import java.nio.file.Files
import java.util.UUID
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** Only owned synthetic app-cache fixtures; never opens the user's Cinderbox tree. */
@RunWith(AndroidJUnit4::class)
class M23CinderboxFirstDeviceTest {
    private lateinit var root: File
    private lateinit var cache: File
    private val marker = ".m23-cinderbox-first-owned"

    @Before fun setup() {
        cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        root = File(cache, "m23-cinderbox-first-${UUID.randomUUID()}")
        assertTrue(root.mkdir())
        File(root, marker).writeText("cinderbox-first-private-fixture-v1\n")
    }

    @After fun cleanup() {
        if (!::root.isInitialized || !root.exists()) return
        val owned = root.parentFile?.canonicalFile == cache &&
            root.name.startsWith("m23-cinderbox-first-") &&
            File(root, marker).takeIf { it.isFile && !Files.isSymbolicLink(it.toPath()) }
                ?.readText() == "cinderbox-first-private-fixture-v1\n"
        if (owned) assertTrue(root.deleteRecursively())
        else fail("Synthetic fixture ownership invalid; no cleanup performed")
    }

    @Test fun m23cb_01ImportedMainGameDoesNotBlockSeparateDestination() {
        val main = File(root, "StardewValley")
        val source = File(main, "desktop/GameFiles")
        assertTrue(source.mkdirs())
        val imported = File(source, "imported-game.zip")
        imported.writeText("synthetic")
        val target = File(root, "Download/StardewValley")
        val result = M23CinderboxFirstPolicy.assess(target, main)
        assertEquals(M23CinderboxFirstPolicy.Code.EMPTY_SEPARATE_DESTINATION, result.code)
        assertFalse(result.authorizesDownload)
        assertFalse(target.exists())
        assertEquals("synthetic", imported.readText())
    }

    @Test fun m23cb_02AllPrimaryCinderboxSubtreesProtected() {
        val main = File(root, "StardewValley")
        assertTrue(main.mkdir())
        for (path in listOf("desktop/GameFiles", "smapi-internal", "desktop/Saves",
                "desktop/Mods", "GameFiles", "Mods", "Saves")) {
            assertEquals(path, M23CinderboxFirstPolicy.Code.PROTECTED_CINDERBOX_TREE,
                M23CinderboxFirstPolicy.assess(File(main, path), main).code)
        }
        assertEquals(M23CinderboxFirstPolicy.Code.PROTECTED_CINDERBOX_TREE,
            M23CinderboxFirstPolicy.assess(root, main).code)
    }

    @Test fun m23cb_03UnsafeAliasAndPartialDownloadFailClosed() {
        val main = File(root, "StardewValley")
        assertTrue(main.mkdir())
        val alias = File(root, "MainAlias")
        Files.createSymbolicLink(alias.toPath(), main.toPath())
        assertEquals(M23CinderboxFirstPolicy.Code.UNSAFE_OR_NONABSOLUTE_DESTINATION,
            M23CinderboxFirstPolicy.assess(File(alias, "desktop/GameFiles"), main).code)
        val target = File(root, "Download/StardewValley")
        assertTrue(target.mkdirs())
        File(target, "partial.zip").writeText("partial")
        assertEquals(M23CinderboxFirstPolicy.Code.EXISTING_OR_PARTIAL_SELECTED_DESTINATION,
            M23CinderboxFirstPolicy.assess(target, main).code)
    }
}
