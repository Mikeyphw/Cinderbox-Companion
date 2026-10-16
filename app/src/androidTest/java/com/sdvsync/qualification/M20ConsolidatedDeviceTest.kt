package com.sdvsync.qualification

import android.content.ComponentName
import android.content.Context
import android.os.SystemClock
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sdvsync.MainActivity
import com.sdvsync.diagnostics.CenterStatus
import com.sdvsync.diagnostics.OperationCenterPolicy
import com.sdvsync.download.GameDownloadRecovery
import com.sdvsync.download.GameDownloadService
import com.sdvsync.download.SmapiTransactionalInstaller
import com.sdvsync.local.InstallHealth
import com.sdvsync.local.InstallationScanner
import com.sdvsync.local.StoragePlanner
import com.sdvsync.mods.BatchModEntry
import com.sdvsync.mods.ModBatchTransaction
import com.sdvsync.mods.ModProfileTransaction
import com.sdvsync.mods.ProfileFolderMove
import com.sdvsync.mods.ModDownloadService
import com.sdvsync.saves.SaveRestoreTransaction
import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** All M20 cases have exclusive private fixtures; failures preserve them. */
open class M20Base {
    @get:Rule val owned = M20FixtureRule()
    protected val work: File get() = owned.fixture.work
    protected fun mkdir(name: String): File = File(work, name).apply { check(mkdir()) }
    protected fun bytes(n: Int = 4096): ByteArray = ByteArray(n) { ((it * 37 + 19) and 255).toByte() }
    protected fun file(name: String, data: String = "owned"): File = File(work, name).apply { writeText(data) }
    protected fun digest(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }
    protected inline fun <reified E: Throwable> rejects(noinline block: () -> Unit) {
        try { block(); fail("Expected ${E::class.java.simpleName}") }
        catch (e: Throwable) { if (e is AssertionError) throw e; if (e !is E) throw e }
    }
    protected fun recovery(): Pair<GameDownloadRecovery, File> {
        val journals = mkdir("journals")
        val dest = mkdir("game")
        return GameDownloadRecovery(journals) to dest
    }
    protected fun center(journals: Set<String> = emptySet(), game: String = "IDLE", mod: String = "IDLE") =
        OperationCenterPolicy.build(game, mod, false, false, false, false, journals, emptyList())
}

open class M20UiBase : M20Base() {
    @get:Rule val activity = createAndroidComposeRule<MainActivity>()
    protected fun signedOut() { activity.onNodeWithText("Continue offline").assertExists() }
    protected fun settings() {
        signedOut()
        activity.onNodeWithText("Settings").performScrollTo().performClick()
        activity.waitForIdle()
    }
    protected fun openOperationCenter() {
        settings()
        // The Settings section heading has no click handler. Scroll to the
        // real navigation button, as qualified by the existing M17 UI tests.
        activity.onNodeWithText("View downloads, mod reviews, sync outcomes and recovery guidance")
            .performScrollTo().performClick()
        activity.waitForIdle()
        activity.onNodeWithText("Live, read-only status and recovery guidance")
            .assertIsDisplayed()
    }
}

/** A: eight service lifecycle and duplication safeguards. Synthetic service is debug-only. */
@RunWith(AndroidJUnit4::class)
class M20AServiceDeviceTest : M20UiBase() {
    private fun app() = InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun a01GameServiceIsNotExported() {
        val info = app().packageManager.getServiceInfo(ComponentName(app(), GameDownloadService::class.java), 0)
        assertFalse(info.exported)
    }
    @Test fun a02ModServiceIsNotExported() {
        val info = app().packageManager.getServiceInfo(ComponentName(app(), ModDownloadService::class.java), 0)
        assertFalse(info.exported)
    }
    @Test fun a03SyntheticWorkerIsNotExported() {
        val info = app().packageManager.getServiceInfo(ComponentName(app(), M20SyntheticWorkerService::class.java), 0)
        assertFalse(info.exported)
    }
    @Test fun a04SyntheticForegroundWorkerWritesPrivateBytes() {
        signedOut(); M20SyntheticWorkerService.start(app(), "a04SyntheticForegroundWorkerWritesPrivateBytes", M20OwnedFixtures.nonce())
        val output = File(work, "synthetic-stream.bin")
        repeat(40) { if (output.length() >= 512) return@repeat; SystemClock.sleep(100) }
        assertTrue("Debug worker did not write", output.length() >= 512)
        M20SyntheticWorkerService.stop(app())
    }
    @Test fun a05WorkerDuplicateStartCannotReplaceFile() {
        signedOut()
        val key = "a05WorkerDuplicateStartCannotReplaceFile"
        M20SyntheticWorkerService.start(app(), key, M20OwnedFixtures.nonce())
        val output = File(work, "synthetic-stream.bin")
        repeat(40) { if (output.length() >= 512) return@repeat; SystemClock.sleep(100) }
        assertTrue(output.length() >= 512)
        M20SyntheticWorkerService.start(app(), key, M20OwnedFixtures.nonce())
        SystemClock.sleep(500)
        assertTrue(output.length() >= 512)
        M20SyntheticWorkerService.stop(app())
    }
    @Test fun a06DuplicateDownloadCheckpointRejected() {
        val (r, dest) = recovery(); r.beginNew(dest, "public", "linux", true)
        rejects<IllegalStateException> { r.beginNew(dest, "public", "linux", true) }
    }
    @Test fun a07MismatchedDownloadSelectionRejected() {
        val (r, dest) = recovery(); r.beginNew(dest, "public", "linux", true)
        rejects<IllegalStateException> { r.requireMatching(dest, "beta", "linux", true) }
    }
    @Test fun a08CancelledWorkerNeverTouchesUnrelatedFile() {
        signedOut(); file("unrelated.txt", "keep-me")
        M20SyntheticWorkerService.start(app(), "a08CancelledWorkerNeverTouchesUnrelatedFile", M20OwnedFixtures.nonce())
        SystemClock.sleep(500); M20SyntheticWorkerService.stop(app())
        SystemClock.sleep(200)
        assertEquals("keep-me", File(work, "unrelated.txt").readText())
    }
}

/** B: deterministic synthetic transport behavior, deliberately not real Steam HTTP. */
private class M20Transfer(private val content: ByteArray) {
    private val out = ArrayList<Byte>()
    var interrupted = false
    fun append(amount: Int) {
        check(!interrupted) { "cancelled" }
        repeat(minOf(amount, content.size - out.size)) { out.add(content[out.size]) }
    }
    fun fail() { interrupted = true }
    fun resume(expectedHash: String) {
        check(MessageDigest.getInstance("SHA-256").digest(content)
            .joinToString("") { "%02x".format(it) } == expectedHash)
        interrupted = false
    }
    fun result() = out.toByteArray()
    fun complete() = out.size == content.size
}
@RunWith(AndroidJUnit4::class)
class M20BNetworkDeviceTest : M20Base() {
    @Test fun b01DeterministicChunkTransferCompletes() {
        val payload=bytes();val t=M20Transfer(payload);t.append(4096);assertArrayEquals(payload,t.result());assertTrue(t.complete())
    }
    @Test fun b02NetworkDropKeepsPartialBytes() {
        val t=M20Transfer(bytes());t.append(700);val old=t.result();t.fail();assertArrayEquals(old,t.result())
    }
    @Test fun b03CancelledSyntheticTransferRejectsMoreWrites() {
        val t=M20Transfer(bytes());t.append(512);t.fail();rejects<IllegalStateException>{t.append(512)}
    }
    @Test fun b04MatchingDigestAllowsExplicitResume() {
        val b=bytes();val t=M20Transfer(b);t.append(500);t.fail();t.resume(digest(b));t.append(4096)
        assertArrayEquals(b,t.result())
    }
    @Test fun b05CorruptDigestBlocksResume() {
        val t=M20Transfer(bytes());t.append(100);t.fail();rejects<IllegalStateException>{t.resume(digest(bytes(100)))}
        assertEquals(100,t.result().size)
    }
    @Test fun b06InterruptedTransferCannotClaimCompletion() {
        val t=M20Transfer(bytes());t.append(200);t.fail();assertFalse(t.complete())
    }
    @Test fun b07ReplayDoesNotDuplicateTransferredBytes() {
        val b=bytes();val t=M20Transfer(b);t.append(900);t.fail();t.resume(digest(b));t.append(b.size)
        assertEquals(b.size,t.result().size);assertArrayEquals(b,t.result())
    }
}

/** C: six fail-closed checkpoint cases and two different-process durability stages. */
@RunWith(AndroidJUnit4::class)
class M20CCrashDeviceTest : M20UiBase() {
    @Test fun c01CheckpointSurvivesNewObject() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        GameDownloadRecovery(File(work,"journals")).requireMatching(d,"public","linux",true)
    }
    @Test fun c02CorruptJournalRejected() {
        val journal=mkdir("journals");File(journal,"m6-game-download.properties").writeText("corrupt")
        rejects<IllegalStateException>{GameDownloadRecovery(journal).pending()}
    }
    @Test fun c03OwnershipMarkerTamperRejectsResume() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        File(d,".cinderbox-download.session").writeText("tampered")
        rejects<IllegalStateException>{r.requireMatching(d,"public","linux",true)}
    }
    @Test fun c04DiscardKeepsPartialBytes() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        val part=File(d,"part.bin").apply{writeBytes(bytes())};r.discard()
        assertArrayEquals(bytes(),part.readBytes());assertNull(r.pending())
    }
    @Test fun c05CompletedClearsOnlyMatchingCheckpoint() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        val part=File(d,"part.bin").apply{writeBytes(bytes())};r.completed()
        assertNull(r.pending());assertArrayEquals(bytes(),part.readBytes())
    }
    @Test fun c06UnownedDirectoryCannotResume() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        val foreign=mkdir("foreign")
        rejects<IllegalStateException>{r.requireMatching(foreign,"public","linux",true)}
    }
    @Test fun c07SeedRunningWorkerBeforeForceStop() {
        signedOut()
        val dir=work
        val journal=File(dir,"journals").apply{check(mkdir())}
        val game=File(dir,"game").apply{check(mkdir())}
        val recovery=GameDownloadRecovery(journal)
        recovery.beginNew(game,"public","linux",true)
        File(game,"partial.bin").writeBytes(bytes())
        M20SyntheticWorkerService.start(InstrumentationRegistry.getInstrumentation().targetContext,
            "c07SeedRunningWorkerBeforeForceStop",M20OwnedFixtures.nonce())
        val stream=File(dir,"synthetic-stream.bin")
        repeat(50){if(stream.length()>=512)return@repeat;SystemClock.sleep(100)}
        assertTrue("Worker never started",stream.length()>=512)
        owned.retainOnSuccess=true
    }
    @Test fun c08VerifyCheckpointAfterProcessDeath() {
        signedOut()
        val previous=M20OwnedFixtures.open("c07SeedRunningWorkerBeforeForceStop")
        val journal=File(previous.work,"journals")
        val game=File(previous.work,"game")
        val stream=File(previous.work,"synthetic-stream.bin")
        assertArrayEquals(bytes(),File(game,"partial.bin").readBytes())
        val recovery=GameDownloadRecovery(journal)
        recovery.requireMatching(game,"public","linux",true)
        val before=stream.length()
        SystemClock.sleep(800)
        assertEquals("Worker unexpectedly resumed after force-stop",before,stream.length())
        rejects<IllegalStateException>{recovery.beginNew(game,"public","linux",true)}
        recovery.discard()
        M20OwnedFixtures.cleanup(previous)
    }
}

/** D: mods, profiles, batch and SMAPI transaction integrity using synthetic trees. */
@RunWith(AndroidJUnit4::class)
class M20DModsDeviceTest : M20Base() {
    @Test fun d01ModProfileRollbackRestoresOriginal() {
        val j=mkdir("journals");val mods=mkdir("mods");File(mods,"alpha").mkdir()
        File(mods,"alpha/original.txt").writeText("keep")
        ModProfileTransaction(j,mods).prepare(listOf(ProfileFolderMove("alpha",".alpha")))
        assertTrue(File(mods,"alpha").renameTo(File(mods,".alpha")))
        assertTrue(ModProfileTransaction(j,mods).recover())
        assertEquals("keep",File(mods,"alpha/original.txt").readText())
    }
    @Test fun d02InterruptedBatchRollsBack() {
        val j=mkdir("journals");val mods=mkdir("mods");val incoming=mkdir("incoming")
        File(mods,"alpha").mkdir();File(mods,"alpha/old.txt").writeText("old")
        File(incoming,"alpha").mkdir();File(incoming,"alpha/new.txt").writeText("new")
        File(incoming,"beta").mkdir();File(incoming,"beta/new.txt").writeText("new")
        rejects<IllegalStateException>{ModBatchTransaction(j,mods).install(
            listOf(BatchModEntry("alpha",File(incoming,"alpha")),BatchModEntry("beta",File(incoming,"beta"))),
            snapshot={},afterStep={ i->if(i==0)error("Injected M20 crash")})}
        assertTrue(ModBatchTransaction(j,mods).recover())
        assertEquals("old",File(mods,"alpha/old.txt").readText())
    }
    @Test fun d03CorruptModBatchJournalFailsClosed() {
        val j=mkdir("journals");val mods=mkdir("mods")
        File(j,"m9-mod-batch.properties").writeText("invalid")
        assertFalse(ModBatchTransaction(j,mods).recover())
        assertTrue(File(j,"m9-mod-batch.properties").exists())
    }
    @Test fun d04SmapiBackupRestoredWhenTargetMissing() {
        val target=File(work,"smapi");val old=File(work,".smapi.sdvsync-backup")
        assertTrue(old.mkdir());File(old,"keep.txt").writeText("original")
        SmapiTransactionalInstaller.recover(target)
        assertEquals("original",File(target,"keep.txt").readText())
    }
    @Test fun d05UnownedSmapiStagePreserved() {
        val target=File(work,"smapi");val staged=File(work,".smapi.sdvsync-stage")
        assertTrue(staged.mkdir());File(staged,"private.txt").writeText("KEEP")
        rejects<IllegalArgumentException>{SmapiTransactionalInstaller.recover(target)}
        assertEquals("KEEP",File(staged,"private.txt").readText())
    }
    @Test fun d06ModReviewRequiresAction() {
        val cards=OperationCenterPolicy.build("IDLE","REVIEW_REQUIRED",false,false,false,true,emptySet(),emptyList())
        assertEquals(CenterStatus.ACTION_REQUIRED,cards.single{it.id=="mod_review"}.status)
    }
    @Test fun d07RecoveryDoesNotMutateUnrelatedGameCheckpoint() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        val mods=mkdir("mods");assertTrue(ModBatchTransaction(File(work,"journals"),mods).recover())
        r.requireMatching(d,"public","linux",true)
    }
}

/** E: transactional save restore and sync conflict policy, no actual user saves. */
@RunWith(AndroidJUnit4::class)
class M20ESavesDeviceTest : M20Base() {
    @Test fun e01SaveRestorePreservesCustomFile() {
        val j=mkdir("journals");val src=mkdir("source");val dst=mkdir("target")
        File(src,"SaveGameInfo").writeText("new");File(dst,"SaveGameInfo").writeText("old")
        File(dst,"custom.json").writeText("keep")
        assertTrue(SaveRestoreTransaction(j).restore(src,dst));assertEquals("keep",File(dst,"custom.json").readText())
    }
    @Test fun e02SaveRecoveryIdempotent() {
        val j=mkdir("journals");val src=mkdir("source");val dst=mkdir("target")
        File(src,"SaveGameInfo").writeText("new");File(dst,"SaveGameInfo").writeText("old")
        assertTrue(SaveRestoreTransaction(j).restore(src,dst))
        assertTrue(SaveRestoreTransaction(j).recover());assertTrue(SaveRestoreTransaction(j).recover())
    }
    @Test fun e03CorruptSaveJournalPreservesLiveFile() {
        val j=mkdir("journals");val dst=mkdir("target");File(dst,"keep").writeText("keep")
        File(j,"m11-save-restore.properties").writeText("bad")
        assertFalse(SaveRestoreTransaction(j).recover());assertEquals("keep",File(dst,"keep").readText())
    }
    @Test fun e04SaveAndDownloadJournalsRemainSeparate() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        val src=mkdir("source");val dst=mkdir("target")
        File(src,"SaveGameInfo").writeText("new");File(dst,"SaveGameInfo").writeText("old")
        assertTrue(SaveRestoreTransaction(File(work,"journals")).restore(src,dst))
        r.requireMatching(d,"public","linux",true)
    }
    @Test fun e05CloudConflictRequiresManualReview() {
        val c=OperationCenterPolicy.build("IDLE","IDLE",false,false,false,false,emptySet(),listOf("CONFLICT"))
        assertEquals(CenterStatus.ACTION_REQUIRED,c.single{it.id=="sync"}.status)
    }
    @Test fun e06StaleSyncPreviewCannotBeReportedCompleted() {
        val c=OperationCenterPolicy.build("IDLE","IDLE",false,false,false,false,emptySet(),listOf("STALE_PREVIEW"))
        assertNotEquals(CenterStatus.COMPLETED,c.single{it.id=="sync"}.status)
    }
}

/** F: permission/storage/path/archive safety checks, strictly fixture-scoped. */
@RunWith(AndroidJUnit4::class)
class M20FStorageDeviceTest : M20Base() {
    @Test fun f01UnknownDownloadSizeNeverMarkedSufficient() {
        val x=StoragePlanner.downloadPlan(work,null);assertNull(x.requiredBytes);assertFalse(x.sufficient==true)
    }
    @Test fun f02EmptyGameInstallNotConsideredComplete() {
        val game=mkdir("game");assertFalse(InstallationScanner.game(game).usable)
    }
    @Test fun f03PartialGameFilesAreNotUsable() {
        val game=mkdir("game");File(game,"Stardew Valley.dll").writeText("partial")
        assertEquals(InstallHealth.INCOMPLETE,InstallationScanner.game(game).health)
    }
    @Test fun f04SymlinkDestinationRejected() {
        val dest=mkdir("game");val link=File(work,"alias")
        Files.createSymbolicLink(link.toPath(),dest.toPath())
        try { rejects<IllegalArgumentException>{GameDownloadRecovery.safeDestination(link)} }
        finally { assertTrue(link.delete()) }
    }
    @Test fun f05SymlinkedPathDoesNotAlterTarget() {
        val dest=mkdir("game");File(dest,"keep").writeText("original")
        val link=File(work,"alias");Files.createSymbolicLink(link.toPath(),dest.toPath())
        try { assertFalse(StoragePlanner.downloadPlan(link,null).sufficient==true)
            assertEquals("original",File(dest,"keep").readText()) }
        finally { assertTrue(link.delete()) }
    }
    @Test fun f06WrongDestinationCannotReuseOwnershipToken() {
        val (r,d)=recovery();r.beginNew(d,"public","linux",true)
        val other=mkdir("other");rejects<IllegalStateException>{r.requireMatching(other,"public","linux",true)}
    }
}

/** G: actual signed-out Compose UI navigation and lifecycle. */
@RunWith(AndroidJUnit4::class)
class M20GUiDeviceTest : M20UiBase() {
    @Test fun g01SignedOutOfflineEntryVisible() { signedOut() }
    @Test fun g02SettingsAvailableWithoutSteam() { settings();activity.onNodeWithText("Operation center").assertExists() }
    @Test fun g03OperationCenterShowsReadOnlyGuidance() {
        openOperationCenter()
        activity.onNodeWithText("No automatic retry or recovery is performed here. Status may be incomplete after Android stops the app.")
            .assertExists()
    }
    @Test fun g04ActivityRecreationStillAllowsOfflineSettings() {
        signedOut();activity.activityRule.scenario.recreate();settings()
    }
    @Test fun g05OperationCenterRefreshIsNonDestructive() {
        file("keep.txt","private-sentinel")
        openOperationCenter()
        activity.onNodeWithText("Refresh checks").performClick()
        activity.waitForIdle()
        activity.onNodeWithText("Live, read-only status and recovery guidance")
            .assertIsDisplayed()
        assertEquals("private-sentinel",File(work,"keep.txt").readText())
    }
}

/** H: concurrency, evidence policy, and reusable fixture ownership. */
@RunWith(AndroidJUnit4::class)
class M20HConcurrencyDeviceTest : M20Base() {
    @Test fun h01ConcurrentCheckpointStartsAreSerialized() {
        val (r,d)=recovery();val gate=CountDownLatch(1);val accepted=AtomicInteger(0)
        val workers=(1..2).map { Thread { gate.await();try{r.beginNew(d,"public","linux",true);accepted.incrementAndGet()}catch(_:IllegalStateException){} } }
        workers.forEach(Thread::start);gate.countDown();workers.forEach{it.join(5000);assertFalse(it.isAlive)}
        assertEquals(1,accepted.get())
    }
    @Test fun h02ConflictingOperationsShowDistinctReviewCards() {
        val cards=OperationCenterPolicy.build("ERROR","REVIEW_REQUIRED",false,false,false,true,
            setOf("download","mod_batch","save_restore"),listOf("CONFLICT"))
        assertEquals(cards.size,cards.map{it.id}.toSet().size)
        assertTrue(cards.count{it.status==CenterStatus.ACTION_REQUIRED}>=5)
    }
    @Test fun h03EvidenceContainsNoFixtureSecrets() {
        val unique="sensitive-private-M20";file("keep.txt",unique)
        val cards=center(setOf("download"));assertFalse(cards.toString().contains(unique))
        assertFalse(cards.toString().contains(work.absolutePath))
    }
    @Test fun h04FixtureOwnershipCannotCrossCaseIds() {
        val wrong="h04FixtureOwnershipCannotCrossCaseIdsDifferent"
        rejects<IllegalStateException>{M20OwnedFixtures.open(wrong)}
    }
    @Test fun h05InventoryIncludesCurrentOwnedFixtureOnlyByOpaqueId() {
        val expected=M20OwnedFixtures.id("h05InventoryIncludesCurrentOwnedFixtureOnlyByOpaqueId")
        assertTrue(M20OwnedFixtures.inventory().contains(expected))
        assertFalse(expected.contains("/"));assertEquals(24,expected.length)
    }
}
