package com.sdvsync.local

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

/** Isolated synthetic Cinderbox tree; never touches a real game or save. */
class M23CinderboxFirstPolicyTest {
    private fun fixtures(block: (File, File) -> Unit) {
        val root = Files.createTempDirectory("m23-cinderbox-policy-").toFile()
        try {
            val original = File(root, "StardewValley").apply { mkdir() }
            block(root, original)
        } finally { root.deleteRecursively() }
    }

    @Test fun importedGameDoesNotBlockSeparateEmptyDownload() = fixtures { root, main ->
        val game = File(main, "desktop/GameFiles").apply { mkdirs() }
        File(game, "imported.zip").writeText("untrusted source; preserve")
        val selected = File(root, "Download/StardewValley")
        val before = File(game, "imported.zip").readText()
        val result = M23CinderboxFirstPolicy.assess(selected, main)
        assertEquals(M23CinderboxFirstPolicy.Code.EMPTY_SEPARATE_DESTINATION, result.code)
        assertTrue(result.separateEmptyDestination)
        assertFalse(result.authorizesDownload)
        assertEquals(before, File(game, "imported.zip").readText())
        assertFalse(selected.exists())
    }

    @Test fun existingEmptySeparateDirectoryIsCandidate() = fixtures { root, main ->
        val selected = File(root, "Download").apply { mkdirs() }
        assertTrue(M23CinderboxFirstPolicy.assess(selected, main).separateEmptyDestination)
    }

    @Test fun mainGameSmapiModsSavesAndRootAreNeverDownloadTargets() = fixtures { root, main ->
        val paths = listOf("", "desktop", "desktop/GameFiles", "smapi-internal",
            "desktop/Saves", "desktop/Mods", "GameFiles", "Mods", "Saves")
        paths.forEach { suffix ->
            assertEquals(suffix, M23CinderboxFirstPolicy.Code.PROTECTED_CINDERBOX_TREE,
                M23CinderboxFirstPolicy.assess(File(main, suffix), main).code)
        }
        assertEquals(M23CinderboxFirstPolicy.Code.PROTECTED_CINDERBOX_TREE,
            M23CinderboxFirstPolicy.assess(root, main).code)
    }

    @Test fun existingUnrelatedPartialFolderIsBlocked() = fixtures { root, main ->
        val selected = File(root, "Download/StardewValley")
        selected.mkdirs()
        File(selected, "game.zip").writeText("unverified archive")
        assertEquals(M23CinderboxFirstPolicy.Code.EXISTING_OR_PARTIAL_SELECTED_DESTINATION,
            M23CinderboxFirstPolicy.assess(selected, main).code)
    }

    @Test fun symlinkAliasesToMainTreeAreRejected() = fixtures { root, main ->
        val symlink = File(root, "Download")
        Files.createSymbolicLink(symlink.toPath(), main.toPath())
        assertEquals(M23CinderboxFirstPolicy.Code.UNSAFE_OR_NONABSOLUTE_DESTINATION,
            M23CinderboxFirstPolicy.assess(File(symlink, "desktop/GameFiles"), main).code)
    }

    @Test fun relativeDestinationCannotBeUsed() = fixtures { _, main ->
        assertEquals(M23CinderboxFirstPolicy.Code.UNSAFE_OR_NONABSOLUTE_DESTINATION,
            M23CinderboxFirstPolicy.assess(File("relative"), main).code)
    }

    @Test fun wordPrefixIsNotPathAncestry() = fixtures { root, main ->
        val sibling = File(root, "StardewValleyBackup/download")
        assertTrue(M23CinderboxFirstPolicy.assess(sibling, main).separateEmptyDestination)
    }
}
