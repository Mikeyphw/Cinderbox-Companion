package com.sdvsync.download

import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.Properties
import java.util.UUID

/** An offline, reviewed repair using a SEPARATE previously verified Steam download.
 * This does not pretend the M6 SHA ledger is a signed Steam manifest: it binds the
 * source to Cinderbox's completed, verified download, not to an arbitrary directory.
 */
data class GameRepairChange(val path: String, val kind: String, val bytes: Long)
data class GameRepairPreview(
    val source: String, val destination: String, val fingerprint: String,
    val changes: List<GameRepairChange>, val preservedFiles: Int, val unchangedFiles: Int
)

class VerifiedGameRepair(
    private val privateRoot: File,
    private val verifiedSource: (File) -> Boolean = { GameFileIntegrity(privateRoot).verifyRecorded(it).passed },
    private val hasPendingDownload: () -> Boolean = { GameDownloadRecovery(privateRoot).pending() != null },
    private val beforeReplace: (Int) -> Unit = {}
) {
    private val journal get() = File(privateRoot, "m10-game-repair.properties")
    private val backupRoot get() = File(privateRoot, "m10-game-repair-backup")
    private val lock = Any()
    private fun exists(f: File) = Files.exists(f.toPath(), LinkOption.NOFOLLOW_LINKS)
    private fun sha(f: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        f.inputStream().buffered().use { input ->
            val buffer = ByteArray(65536)
            while (true) { val n = input.read(buffer); if (n < 0) break; md.update(buffer, 0, n) }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
    private fun shaString(s: String): String = MessageDigest.getInstance("SHA-256")
        .digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

    private fun safeRoot(root: File): File {
        val safe = GameDownloadRecovery.safeDestination(root)
        check(safe.isDirectory && safe.canRead()) { "Game directory must exist and be readable" }
        return safe
    }
    private fun child(root: File, rel: String): File {
        require(rel.isNotBlank() && !rel.startsWith('/') && '\\' !in rel && '\u0000' !in rel &&
            rel.split('/').none { it.isBlank() || it == "." || it == ".." }) { "Unsafe relative file path" }
        val f = File(root, rel)
        check(f.canonicalPath.startsWith(root.canonicalPath + File.separator)) { "File escaped game root" }
        var part: File? = f.absoluteFile
        while (part != null) {
            check(!Files.isSymbolicLink(part.toPath())) { "Symlink in game file path" }
            part = part.parentFile
        }
        return f
    }
    private fun gameFiles(root: File): Map<String, File> {
        val result = linkedMapOf<String, File>()
        root.walkTopDown().onEnter { dir ->
            check(!Files.isSymbolicLink(dir.toPath())) { "Symlink in game tree" }
            dir == root || (dir.name != ".DepotDownloader" && !dir.name.startsWith(".cinderbox-m10-"))
        }.forEach { f ->
            check(!Files.isSymbolicLink(f.toPath())) { "Symlink in game tree" }
            if (f.isFile && f.name != ".cinderbox-download.session") {
                val rel = f.relativeTo(root).invariantSeparatorsPath
                child(root, rel)
                result[rel] = f
            }
        }
        return result
    }
    private fun validatePair(sourceDir: File, destinationDir: File): Pair<File, File> {
        val source = safeRoot(sourceDir)
        val dest = safeRoot(destinationDir)
        check(source != dest && !dest.path.startsWith(source.path + File.separator) &&
            !source.path.startsWith(dest.path + File.separator)) { "Source and target must be separate game directories" }
        check(dest.canWrite()) { "Target installation not writable" }
        check(verifiedSource(source)) {
            "Source does not match the completed download's integrity record"
        }
        check(!hasPendingDownload()) {
            "Resolve the interrupted Steam download before repairing files"
        }
        check(File(dest, "Stardew Valley.dll").isFile ||
            File(dest, "StardewValley.GameData.dll").isFile || File(dest, "Content").isDirectory) {
            "Destination is not a recognized existing game; use a new download instead"
        }
        return source to dest
    }
    private data class Planned(val rel: String, val previous: String, val wanted: String, val length: Long)
    private fun collect(source: File, dest: File): Triple<List<Planned>, Int, Int> {
        val incoming = gameFiles(source)
        val existing = gameFiles(dest)
        val changes = mutableListOf<Planned>()
        var unchanged = 0
        for ((rel, src) in incoming) {
            val destinationFile = child(dest, rel)
            check(!exists(destinationFile) || destinationFile.isFile) {
                "Game file would collide with a directory: $rel"
            }
            val old = existing[rel]
            val oldDigest = old?.let { sha(it) } ?: ""
            val newDigest = sha(src)
            if (oldDigest == newDigest) unchanged++
            else changes += Planned(rel, oldDigest, newDigest, src.length())
        }
        return Triple(changes.sortedBy { it.rel }, existing.keys.subtract(incoming.keys).size, unchanged)
    }
    private fun fingerprint(source: File, dest: File, entries: List<Planned>): String = shaString(buildString {
        append(source.canonicalPath).append('\n').append(dest.canonicalPath).append('\n')
        entries.forEach { append(it.rel).append('\u0000').append(it.previous).append('\u0000')
            .append(it.wanted).append('\u0000').append(it.length).append('\n') }
    })

    /** Reads only. Never edits or adopts an existing destination implicitly. */
    fun preview(sourceDir: File, destinationDir: File): GameRepairPreview = synchronized(lock) {
        check(!exists(journal)) { "An interrupted game repair needs recovery first" }
        val (source, dest) = validatePair(sourceDir, destinationDir)
        val (items, preserved, same) = collect(source, dest)
        GameRepairPreview(source.path, dest.path, fingerprint(source, dest, items),
            items.map { GameRepairChange(it.rel, if (it.previous.isEmpty()) "ADD" else "REPLACE", it.length) },
            preserved, same)
    }

    private data class Recovery(val dest: File, val stage: File, val plans: List<Planned>)
    private fun readJournal(): Recovery? {
        if (!journal.isFile || Files.isSymbolicLink(journal.toPath()) || journal.length() !in 1..10_485_760) return null
        val props = runCatching { Properties().apply { journal.inputStream().use { load(it) } } }.getOrNull() ?: return null
        if (props.getProperty("schema") != "1") return null
        val dest = runCatching { safeRoot(File(props.getProperty("destination") ?: return null)) }.getOrNull() ?: return null
        val stageName = props.getProperty("stage") ?: return null
        if (!stageName.matches(Regex("\\.cinderbox-m10-[0-9a-f-]{36}"))) return null
        val stage = File(dest, stageName)
        if (stage.exists() && (!stage.isDirectory || Files.isSymbolicLink(stage.toPath()))) return null
        val count = props.getProperty("count")?.toIntOrNull() ?: return null
        if (count !in 1..100000) return null
        val plans = (0 until count).map { i ->
            val path = props.getProperty("path.$i") ?: return null
            val old = props.getProperty("old.$i") ?: return null
            val next = props.getProperty("new.$i") ?: return null
            val size = props.getProperty("size.$i")?.toLongOrNull() ?: return null
            if (!(old.isEmpty() || old.matches(Regex("[0-9a-f]{64}"))) ||
                !next.matches(Regex("[0-9a-f]{64}")) || size < 0L ||
                runCatching { child(dest, path) }.isFailure) return null
            Planned(path, old, next, size)
        }
        if (plans.map { it.rel }.distinct().size != count) return null
        return Recovery(dest, stage, plans)
    }
    private fun writeJournal(dest: File, stage: File, plans: List<Planned>) {
        check(!exists(journal)) { "Another repair is pending" }
        val p = Properties().apply {
            setProperty("schema", "1"); setProperty("destination", dest.canonicalPath)
            setProperty("stage", stage.name); setProperty("count", plans.size.toString())
            plans.forEachIndexed { i, it ->
                setProperty("path.$i", it.rel); setProperty("old.$i", it.previous)
                setProperty("new.$i", it.wanted); setProperty("size.$i", it.length.toString())
            }
        }
        check(privateRoot.isDirectory || privateRoot.mkdirs())
        val tmp = File(privateRoot, ".m10-repair-${UUID.randomUUID()}.tmp")
        try {
            FileOutputStream(tmp).use { stream -> p.store(stream, "M10 repair rollback journal"); stream.fd.sync() }
            Files.move(tmp.toPath(), journal.toPath(), StandardCopyOption.ATOMIC_MOVE)
        } finally { tmp.delete() }
    }
    private fun atomicReplace(staged: File, target: File) {
        check(!Files.isSymbolicLink(target.toPath())) { "Target changed to a symlink" }
        target.parentFile?.let { check(it.isDirectory || it.mkdirs()) }
        Files.move(staged.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE,
            StandardCopyOption.REPLACE_EXISTING)
    }
    private fun cleanWorkspace(stage: File): Boolean {
        if (!exists(stage)) return true
        if (!stage.isDirectory || Files.isSymbolicLink(stage.toPath())) return false
        // The stage lives on shared storage: never delete unrelated files planted in it.
        val allowed = Regex("(?:[0-9]+|rollback-[0-9]+)\\.bin")
        if (stage.listFiles()?.any { !it.isFile || Files.isSymbolicLink(it.toPath()) ||
                !allowed.matches(it.name) } != false) return false
        return stage.deleteRecursively()
    }

    /** Roll back only if every affected target still equals its original or our intended bytes. */
    fun recover(): Boolean = synchronized(lock) {
        if (!exists(journal)) return true
        val recovery = readJournal() ?: return false
        // Check the complete batch before modifying the first file.
        for ((i, plan) in recovery.plans.withIndex()) {
            val target = runCatching { child(recovery.dest, plan.rel) }.getOrElse { return false }
            if (exists(target) && !target.isFile) return false
            val actual = if (exists(target)) runCatching { sha(target) }.getOrElse { return false } else ""
            if (actual != plan.previous && actual != plan.wanted) return false
            if (plan.previous.isNotEmpty()) {
                val backup = File(backupRoot, "$i.bin")
                if (!backup.isFile || Files.isSymbolicLink(backup.toPath()) ||
                    runCatching { sha(backup) != plan.previous }.getOrDefault(true)) return false
            }
        }
        for ((i, plan) in recovery.plans.withIndex()) {
            val target = child(recovery.dest, plan.rel)
            val actual = if (exists(target)) sha(target) else ""
            if (actual == plan.previous) continue
            if (plan.previous.isEmpty()) {
                if (!target.delete()) return false
            } else {
                val stageFile = File(recovery.stage, "rollback-$i.bin")
                check(recovery.stage.isDirectory || recovery.stage.mkdirs())
                File(backupRoot, "$i.bin").copyTo(stageFile, overwrite = false)
                if (sha(stageFile) != plan.previous) return false
                atomicReplace(stageFile, target)
            }
        }
        if (!cleanWorkspace(recovery.stage)) return false
        if (!journal.delete()) return false
        backupRoot.deleteRecursively()
        true
    }

    /** Applies only ADD/REPLACE entries. Destination-only files are never removed. */
    fun apply(review: GameRepairPreview): Int = synchronized(lock) {
        check(recover()) { "Unresolved prior repair; manual review required" }
        val live = preview(File(review.source), File(review.destination))
        check(live.fingerprint == review.fingerprint && live.changes == review.changes) {
            "Game files changed since review; scan again"
        }
        if (live.changes.isEmpty()) return 0
        val (source, dest) = validatePair(File(review.source), File(review.destination))
        val plans = collect(source, dest).first
        check(plans.size == live.changes.size)
        check(!exists(backupRoot) && !exists(journal)) { "Unresolved previous repair data" }
        val stage = File(dest, ".cinderbox-m10-${UUID.randomUUID()}")
        check(stage.mkdir()) { "Cannot prepare repair staging area" }
        check(backupRoot.mkdir()) { "Cannot retain repair originals" }
        var published = false
        try {
            for ((i, plan) in plans.withIndex()) {
                val origin = child(source, plan.rel)
                val target = child(dest, plan.rel)
                if (plan.previous.isNotEmpty()) {
                    val backup = File(backupRoot, "$i.bin")
                    target.copyTo(backup, overwrite = false)
                    check(sha(backup) == plan.previous) { "Destination changed before backup" }
                }
                val staged = File(stage, "$i.bin")
                origin.copyTo(staged, overwrite = false)
                check(sha(staged) == plan.wanted) { "Verified source changed while staging" }
            }
            writeJournal(dest, stage, plans)
            published = true
            for ((i, plan) in plans.withIndex()) {
                val target = child(dest, plan.rel)
                val current = if (exists(target)) sha(target) else ""
                check(current == plan.previous) { "Destination changed before repair" }
                beforeReplace(i)
                atomicReplace(File(stage, "$i.bin"), target)
            }
            check(cleanWorkspace(stage)) { "Cannot finalize staged repair" }
            check(journal.delete()) { "Cannot finalize repair journal" }
            backupRoot.deleteRecursively()
            plans.size
        } catch (e: Exception) {
            if (published) {
                check(recover()) { "Repair stopped; manual recovery required before further edits" }
            } else {
                cleanWorkspace(stage); backupRoot.deleteRecursively()
            }
            throw e
        }
    }
}
