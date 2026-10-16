package com.sdvsync.qualification

import android.content.Context
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import org.junit.rules.TestWatcher
import org.junit.runner.Description

/** M20 test-only, app-private fixture registry. No production path is ever supplied. */
object M20OwnedFixtures {
    private const val PREFIX = "m20-owned-"
    private const val ROOT_MARKER = ".m20-fixtures-v1"
    private const val MARKER = ".m20-owned-v1"
    private fun digest(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    private fun base(): File {
        val files = InstrumentationRegistry.getInstrumentation().targetContext.filesDir.canonicalFile
        check(files.isDirectory && files.canWrite() && !Files.isSymbolicLink(files.toPath())) {
            "M20_CANONICAL_PRIVATE_STORAGE_UNAVAILABLE"
        }
        val parent = File(files, "m20-qualification-fixtures")
        val newRoot = !parent.exists()
        if (newRoot) check(parent.mkdir()) { "M20_FIXTURE_ROOT_UNAVAILABLE" }
        check(parent.isDirectory && !Files.isSymbolicLink(parent.toPath()) &&
            parent.canonicalFile.parentFile == files) { "M20_FIXTURE_ROOT_UNTRUSTED" }
        val marker = File(parent, ROOT_MARKER)
        if (newRoot) check(marker.createNewFile().also { if (it) marker.writeText("m20-v1") })
        check(marker.isFile && !Files.isSymbolicLink(marker.toPath()) && marker.readText() == "m20-v1") {
            "M20_FIXTURE_ROOT_OWNERSHIP_UNVERIFIED"
        }
        return parent
    }
    fun nonce(): String {
        val token = InstrumentationRegistry.getArguments().getString("m20_nonce") ?: ""
        require(Regex("[0-9a-f]{32}").matches(token)) { "M20_NONCE_INVALID" }
        return token
    }
    fun id(caseId: String, token: String = nonce()): String {
        require(Regex("[a-h][0-9]{2}[A-Za-z0-9]+").matches(caseId)) { "M20_CASE_INVALID" }
        require(Regex("[0-9a-f]{32}").matches(token)) { "M20_NONCE_INVALID" }
        return digest("m20-v1:$token:$caseId").take(24)
    }
    private fun ownedDir(caseId: String, token: String): File = File(base(), PREFIX + id(caseId, token))
    data class Fixture(val dir: File, val caseId: String, val token: String) {
        val work: File get() = File(dir, "work")
        fun file(name: String): File = File(work, name)
        fun keep(): Fixture = this
    }
    fun create(caseId: String, token: String = nonce()): Fixture {
        val dir = ownedDir(caseId, token)
        check(!dir.exists() && !Files.isSymbolicLink(dir.toPath())) { "M20_FIXTURE_COLLISION" }
        check(dir.mkdir()) { "M20_FIXTURE_CREATE_FAILED" }
        val owner = File(dir, MARKER)
        check(owner.createNewFile()) { "M20_FIXTURE_MARKER_FAILED" }
        owner.writeText("m20-v1:$caseId:${id(caseId, token)}:$token")
        check(File(dir, "work").mkdir()) { "M20_FIXTURE_WORK_UNAVAILABLE" }
        return Fixture(dir, caseId, token)
    }
    fun open(caseId: String, token: String = nonce()): Fixture {
        val fixture = Fixture(ownedDir(caseId, token), caseId, token)
        val dir = fixture.dir
        check(dir.isDirectory && !Files.isSymbolicLink(dir.toPath()) && dir.parentFile == base()) {
            "M20_FIXTURE_NOT_OWNED"
        }
        val marker = File(dir, MARKER)
        check(marker.isFile && marker.length() < 256 && !Files.isSymbolicLink(marker.toPath()) &&
            marker.readText() == "m20-v1:$caseId:${id(caseId, token)}:$token" &&
            fixture.work.isDirectory && !Files.isSymbolicLink(fixture.work.toPath())) {
            "M20_FIXTURE_NOT_OWNED"
        }
        return fixture
    }
    private fun safeWalk(file: File, depth: Int = 0) {
        check(depth <= 12 && !Files.isSymbolicLink(file.toPath())) { "M20_FIXTURE_CLEANUP_UNSAFE" }
        if (file.isDirectory) {
            val children = file.listFiles() ?: error("M20_FIXTURE_NOT_READABLE")
            check(children.size <= 256) { "M20_FIXTURE_TOO_MANY_ENTRIES" }
            children.forEach { safeWalk(it, depth + 1) }
        } else check(file.isFile && file.length() <= 8 * 1024 * 1024) { "M20_FIXTURE_UNKNOWN_ENTRY" }
    }
    fun cleanup(fixture: Fixture) {
        val checked = open(fixture.caseId, fixture.token)
        // Never traverse any directory except this exact owned subtree.
        check(checked.dir.list()?.toSet() == setOf(MARKER, "work")) {
            "M20_FIXTURE_UNEXPECTED_TOP_LEVEL_ENTRY"
        }
        safeWalk(checked.work)
        fun delete(file: File) {
            if (file.isDirectory) file.listFiles()!!.forEach(::delete)
            check(file.delete()) { "M20_FIXTURE_CLEANUP_FAILED" }
        }
        delete(checked.work)
        check(File(checked.dir, MARKER).delete() && checked.dir.delete()) {
            "M20_FIXTURE_CLEANUP_FAILED"
        }
    }
    /** Read-only inventory: no directory or marker creation. Legacy M19 stays unverified. */
    fun inventory(): List<String> {
        val files = InstrumentationRegistry.getInstrumentation().targetContext.filesDir.canonicalFile
        check(files.isDirectory && !Files.isSymbolicLink(files.toPath()))
        val existing = File(files, "m20-qualification-fixtures")
        val marker = File(existing, ROOT_MARKER)
        val trusted = existing.isDirectory && !Files.isSymbolicLink(existing.toPath()) &&
            marker.isFile && !Files.isSymbolicLink(marker.toPath()) &&
            marker.readText() == "m20-v1"
        check(!existing.exists() || trusted) { "M20_INVENTORY_ROOT_UNTRUSTED" }
        val names = (if (trusted) existing.listFiles()?.asList().orEmpty() else emptyList())
            .filter { it.name.matches(Regex("m20-owned-[0-9a-f]{24}")) }
            .map { it.name.removePrefix(PREFIX) }.sorted()
        val legacy = InstrumentationRegistry.getInstrumentation().targetContext.filesDir.canonicalFile
            .listFiles()?.filter { it.name.matches(Regex("m19-test-only-[0-9a-f]{24}")) }
            ?.map { "m19-unverified:" + it.name.removePrefix("m19-test-only-") }?.sorted().orEmpty()
        return names + legacy
    }
    /** Only a known, previously created and verified M20 fixture may be removed. */
    fun cleanupByOpaqueId(expectedId: String) {
        require(Regex("[0-9a-f]{24}").matches(expectedId)) { "M20_CLEANUP_ID_INVALID" }
        val dir = File(base(), PREFIX + expectedId)
        val marker = File(dir, MARKER)
        check(marker.isFile && !Files.isSymbolicLink(marker.toPath()) && marker.length() < 256) {
            "M20_CLEANUP_OWNERSHIP_UNVERIFIED"
        }
        val parts = marker.readText().split(':')
        check(parts.size == 4 && parts[0] == "m20-v1" && parts[2] == expectedId &&
            Regex("[a-h][0-9]{2}[A-Za-z0-9]+").matches(parts[1]) &&
            Regex("[0-9a-f]{32}").matches(parts[3]) && id(parts[1], parts[3]) == expectedId) {
            "M20_CLEANUP_OWNERSHIP_UNVERIFIED"
        }
        cleanup(open(parts[1], parts[3]))
    }
    fun cleanupLegacyM19(expectedId: String) {
        require(Regex("[0-9a-f]{24}").matches(expectedId)) { "M19_LEGACY_ID_INVALID" }
        val root = File(InstrumentationRegistry.getInstrumentation().targetContext.filesDir.canonicalFile,
            "m19-test-only-$expectedId")
        check(root.isDirectory && !Files.isSymbolicLink(root.toPath()) &&
            root.list()?.toSet() == setOf("checkpoint", "game")) { "M19_LEGACY_OWNERSHIP_UNVERIFIED" }
        val checkpoint = File(root, "checkpoint")
        val game = File(root, "game")
        val journal = File(checkpoint, "m6-game-download.properties")
        val session = File(game, ".cinderbox-download.session")
        val partial = File(game, "synthetic-partial.bin")
        check(checkpoint.isDirectory && game.isDirectory &&
            checkpoint.list()?.toSet() == setOf(journal.name) &&
            game.list()?.toSet() == setOf(session.name, partial.name) &&
            listOf(journal, session, partial).all { it.isFile && !Files.isSymbolicLink(it.toPath()) } &&
            partial.length() == 4096L) { "M19_LEGACY_OWNERSHIP_UNVERIFIED" }
        val content=ByteArray(4096) { i -> ((i * 37 + 19) and 255).toByte() }
        check(partial.readBytes().contentEquals(content)) { "M19_LEGACY_DATA_UNVERIFIED" }
        val recovery = com.sdvsync.download.GameDownloadRecovery(checkpoint)
        val record = recovery.pending()
        check(record != null && record.matches(game, "public", "linux", true)) {
            "M19_LEGACY_JOURNAL_UNVERIFIED"
        }
        check(partial.delete() && session.delete() && journal.delete() &&
            game.delete() && checkpoint.delete() && root.delete()) { "M19_LEGACY_CLEANUP_FAILED" }
    }
}

/** Failed cases leave owned fixtures in the persistent inventory for diagnosis. */
class M20FixtureRule : TestWatcher() {
    lateinit var fixture: M20OwnedFixtures.Fixture
    var retainOnSuccess: Boolean = false
    override fun starting(description: Description) {
        fixture = M20OwnedFixtures.create(description.methodName)
    }
    override fun succeeded(description: Description) {
        if (!retainOnSuccess) M20OwnedFixtures.cleanup(fixture)
    }
}
