package com.sdvsync.download

import java.io.File
import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class M24SteamBuildCheckpointTest {
    private fun fixture(block: (File, File, GameDownloadRecovery) -> Unit) {
        val root = Files.createTempDirectory("m24-journal-").toFile()
        val owner = File(root, "private").apply { mkdir() }
        val game = File(root, "game").apply { mkdir() }
        try { block(owner, game, GameDownloadRecovery(owner)) }
        finally { root.deleteRecursively() }
    }
    @Test fun checkpointBuildSurvivesColdObjectRecovery() = fixture { owner,game,r ->
        r.beginNew(game,"public","windows",true)
        r.bindSteamBuildId(7724)
        val again = GameDownloadRecovery(owner)
        assertEquals(7724L, again.pending()!!.steamBuildId)
        again.requireMatching(game,"public","windows",true)
        again.requireSteamBuildId(7724)
    }
    @Test fun oldJournalNeverAuthorizesLiveM24() = fixture { _,game,r ->
        r.beginNew(game,"public","windows",true)
        assertEquals(0L,r.pending()!!.steamBuildId)
        assertThrows(IllegalStateException::class.java) { r.requireSteamBuildId(77) }
    }
    @Test fun mismatchedBuildNeverChangesPartialFile() = fixture { _,game,r ->
        r.beginNew(game,"public","windows",true)
        r.bindSteamBuildId(13)
        File(game,"incomplete").writeText("keep")
        assertThrows(IllegalStateException::class.java) { r.requireSteamBuildId(14) }
        assertThrows(IllegalStateException::class.java) { r.bindSteamBuildId(14) }
        assertEquals("keep", File(game,"incomplete").readText())
    }
    @Test fun invalidJournalBuildBlocks() = fixture { owner,game,r ->
        r.beginNew(game,"public","windows",true)
        r.bindSteamBuildId(13)
        val journal = File(owner,"m6-game-download.properties")
        journal.appendText("steam_build_id=invalid\n")
        assertThrows(IllegalStateException::class.java) { r.pending() }
    }
}
