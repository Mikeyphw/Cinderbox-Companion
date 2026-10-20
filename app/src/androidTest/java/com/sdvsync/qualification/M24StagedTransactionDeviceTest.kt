package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.download.GameDownloadRecovery
import java.io.File
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** All fixtures are private app cache; no Steam, installed game, saves or mods. */
@RunWith(AndroidJUnit4::class)
class M24StagedTransactionDeviceTest {
    private fun fixture(block: (GameDownloadRecovery, File) -> Unit) {
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        val root = File(cache, "m24stage-owned-${UUID.randomUUID()}")
        assertTrue(root.mkdir())
        val owner = File(root, "owner").apply { assertTrue(mkdir()) }
        val game = File(root, "new-game")
        try { block(GameDownloadRecovery(owner), game) }
        finally {
            assertEquals(cache, root.canonicalFile.parentFile)
            assertTrue(root.name.startsWith("m24stage-owned-"))
            assertTrue(root.deleteRecursively())
        }
    }
    private fun rejects(block: () -> Unit) {
        try { block(); fail("Expected fail-closed rejection") }
        catch (_: IllegalStateException) { }
    }
    @Test fun m24s_01StageNeverTouchesSelectedFinalPath() = fixture { r, game ->
        r.beginStaged(game, "public", "windows", true)
        r.bindSteamBuildId(7)
        File(r.requireActiveStage(game), "part.dat").writeText("private")
        assertFalse(game.exists())
    }
    @Test fun m24s_02BuildDriftPreservesPartialStage() = fixture { r, game ->
        r.beginStaged(game, "public", "windows", true)
        r.bindSteamBuildId(7)
        val payload = File(r.requireActiveStage(game), "part.dat").apply { writeText("private") }
        rejects { r.requireSteamBuildId(8) }
        assertEquals("private", payload.readText())
    }
    @Test fun m24s_03AtomicPromotionAndColdReconciliation() = fixture { r, game ->
        r.beginStaged(game, "public", "windows", true)
        r.bindSteamBuildId(7)
        File(r.requireActiveStage(game), "part.dat").writeText("private")
        r.promoteStaged(game)
        assertTrue(r.isPromotedStage(game))
        GameDownloadRecovery(game.parentFile.resolve("owner")).completed()
        assertTrue(game.resolve("part.dat").isFile)
    }
    @Test fun m24s_04DiscardPreservesPartialFiles() = fixture { r, game ->
        r.beginStaged(game, "public", "windows", true)
        r.bindSteamBuildId(7)
        val stage = r.requireActiveStage(game)
        File(stage, "part.dat").writeText("keep")
        r.discard()
        assertEquals("keep", File(stage, "part.dat").readText())
        assertFalse(game.exists())
    }
}
