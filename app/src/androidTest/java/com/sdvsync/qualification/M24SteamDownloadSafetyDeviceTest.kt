package com.sdvsync.qualification

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.download.GameDownloadRecovery
import com.sdvsync.download.M24SteamSelectionPolicy
import java.io.File
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Four isolated app-cache cases; NEVER connects to Steam or real game storage. */
@RunWith(AndroidJUnit4::class)
class M24SteamDownloadSafetyDeviceTest {
    private fun fixture(test: (GameDownloadRecovery, File) -> Unit) {
        val cache = InstrumentationRegistry.getInstrumentation().targetContext.cacheDir.canonicalFile
        val root = File(cache, "m24-owned-${UUID.randomUUID()}")
        assertTrue(root.mkdir())
        val owner = File(root,"private").apply { assertTrue(mkdir()) }
        val game = File(root,"game").apply { assertTrue(mkdir()) }
        try { test(GameDownloadRecovery(owner),game) }
        finally {
            assertTrue(root.canonicalFile.parentFile == cache)
            assertTrue(root.name.startsWith("m24-owned-"))
            assertTrue(root.deleteRecursively())
        }
    }
    private fun rejects(block: () -> Unit) {
        try { block(); fail("Expected rejection") }
        catch (_: IllegalStateException) { }
    }
    @Test fun m24_01AuthenticatedBranchBuildGateFailClosed() {
        assertEquals(M24SteamSelectionPolicy.Verdict.SIGNED_OUT,
            M24SteamSelectionPolicy.assess(false,1,1))
        assertEquals(M24SteamSelectionPolicy.Verdict.BRANCH_CHANGED,
            M24SteamSelectionPolicy.assess(true,1,2))
    }
    @Test fun m24_02FreshCheckpointCannotResumeWithoutBuild() = fixture { r,dir ->
        r.beginNew(dir,"public","linux",true)
        rejects { r.requireSteamBuildId(5) }
    }
    @Test fun m24_03BoundBuildSurvivesColdRecovery() = fixture { r,dir ->
        r.beginNew(dir,"public","linux",true)
        r.bindSteamBuildId(5)
        r.requireSteamBuildId(5)
        assertEquals(5L,r.pending()!!.steamBuildId)
    }
    @Test fun m24_04DriftLeavesOwnedPartialBytesUntouched() = fixture { r,dir ->
        r.beginNew(dir,"public","linux",true)
        r.bindSteamBuildId(5)
        val bytes = File(dir,"partial.bin").apply { writeText("synthetic") }
        rejects { r.requireSteamBuildId(6) }
        assertEquals("synthetic",bytes.readText())
    }
}
