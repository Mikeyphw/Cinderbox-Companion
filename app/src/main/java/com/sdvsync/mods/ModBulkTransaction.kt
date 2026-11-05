package com.sdvsync.mods

import com.sdvsync.local.PlatformStoragePaths
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.Path
import java.nio.file.attribute.BasicFileAttributes
import java.security.MessageDigest
import java.util.Locale
import java.util.Properties
import java.util.UUID

/** A review for one exact, immutable set of reversible folder changes. Never a UI token alone. */
internal data class BulkFolderReview(
    val identity: String,
    val inventoryFingerprint: String,
    val rootWitness: String,
    val moves: List<ProfileFolderMove>,
    val sourceHashes: List<String>
)

/**
 * M25-03 R2A fixture-qualified engine. There is deliberately no UI/production call to apply.
 * One app-private journal covers the whole batch; a crash always rolls BACK, never resumes.
 * Byte digests and root direct-child identity are checked before each mutation/recovery.
 */
internal class ModBulkTransaction(private val privateRoot: File, private val modsDir: File) {
    companion object {
        private val processLock = Any()
        private const val MAX_STEPS = 512
        private const val MAX_FILES = 100_000
        private const val MAX_DEPTH = 48
        private const val MAX_BYTES = 1024L * 1024L * 1024L // Fail closed, not partial hashing.
        private const val JOURNAL_NAME = "m25-bulk-transaction.properties"
    }
    private val journal get() = File(privateRoot, JOURNAL_NAME)
    private val usedTokens = mutableSetOf<String>()

    private fun exists(f: File): Boolean = Files.exists(f.toPath(), LinkOption.NOFOLLOW_LINKS)
    private fun sha(): MessageDigest = MessageDigest.getInstance("SHA-256")
    private fun hex(bytes: ByteArray): String = bytes.joinToString("") { "%02x".format(it) }
    private fun MessageDigest.text(text: String) { update(text.toByteArray(Charsets.UTF_8)); update(0) }
    private fun attrs(file: File): BasicFileAttributes = Files.readAttributes(
        file.toPath(), BasicFileAttributes::class.java, LinkOption.NOFOLLOW_LINKS)
    private fun validName(name: String) = name.isNotBlank() && name != "." && name != ".." &&
        !name.startsWith("..") && name.none { it == '/' || it == '\\' || it.isISOControl() }

    private fun root(): File {
        require(PlatformStoragePaths.inspect(modsDir).safe) { "Unsafe Mods storage" }
        require(modsDir.isAbsolute && modsDir.isDirectory && modsDir.canRead() && modsDir.canWrite()) {
            "Mods storage unavailable"
        }
        require(!Files.isSymbolicLink(modsDir.toPath())) { "Mods root is a symlink" }
        return modsDir.canonicalFile
    }

    private fun child(name: String, canonicalRoot: File): File {
        require(validName(name)) { "Unsafe direct-child name" }
        val file = File(modsDir, name)
        require(!Files.isSymbolicLink(file.toPath())) { "Symlinked mod path" }
        require(file.canonicalFile.parentFile == canonicalRoot) { "Mod path escaped Mods" }
        return file
    }

    private fun validateMoves(moves: List<ProfileFolderMove>, canonicalRoot: File): List<File> {
        require(moves.size in 1..MAX_STEPS) { "Bulk size must be 1..512" }
        val source = moves.map { child(it.from, canonicalRoot) }
        val target = moves.map { child(it.to, canonicalRoot) }
        val from = moves.map { it.from.lowercase(Locale.ROOT) }
        val to = moves.map { it.to.lowercase(Locale.ROOT) }
        require(from.distinct().size == moves.size && to.distinct().size == moves.size &&
            from.toSet().intersect(to.toSet()).isEmpty()) { "Ambiguous source or destination" }
        moves.forEach { move ->
            require(move.from != move.to &&
                (if (move.from.startsWith('.')) move.from.drop(1) == move.to
                 else ".${move.from}" == move.to)) { "Only exact SMAPI dot toggles are allowed" }
        }
        // Filesystems can be case insensitive. Even unrelated collisions are unsafe.
        val names = requireNotNull(modsDir.listFiles()) { "Mods inventory unavailable" }
            .map { it.name.lowercase(Locale.ROOT) }
        require(names.size == names.toSet().size) { "Case-folded Mods collision" }
        source.forEach { require(it.isDirectory && !Files.isSymbolicLink(it.toPath())) {
            "Source missing or not a directory" } }
        target.forEach { require(!exists(it)) { "Destination already exists" } }
        return source
    }

    /** Read every regular byte in a mod subtree. Never follow symlinks or special files. */
    private fun treeHash(directory: File): String {
        require(directory.isDirectory && !Files.isSymbolicLink(directory.toPath())) {
            "Missing or linked mod folder" }
        val digest = sha()
        val budget = longArrayOf(0L, 0L)
        fun walk(node: File, relative: String, depth: Int) {
            require(depth <= MAX_DEPTH) { "Mod directory nesting exceeds limit" }
            val a = attrs(node)
            require(!a.isSymbolicLink && !a.isOther) { "Special or linked mod entry" }
            budget[0]++
            require(budget[0] <= MAX_FILES) { "Too many mod files" }
            // Reject shared inodes where the platform exposes a POSIX hard-link count.
            val nlink = runCatching {
                Files.getAttribute(node.toPath(), "unix:nlink", LinkOption.NOFOLLOW_LINKS)
            }.getOrNull()
            require(nlink !is Number || nlink.toLong() <= 1L || a.isDirectory) {
                "Shared hardlink in mod folder" }
            if (a.isDirectory) {
                digest.text("D:$relative")
                val children = requireNotNull(node.listFiles()) { "Unreadable mod directory" }
                    .sortedBy { it.name }
                children.forEach { file ->
                    require(file.name != "." && file.name != ".." && !file.name.contains('/')) {
                        "Invalid directory entry" }
                    walk(file, if (relative.isEmpty()) file.name else "$relative/${file.name}", depth + 1)
                }
            } else {
                require(a.isRegularFile && a.size() >= 0L) { "Non-file mod entry" }
                budget[1] += a.size()
                require(budget[1] <= MAX_BYTES) { "Mod data exceeds bounded review" }
                digest.text("F:$relative:${a.size()}")
                FileInputStream(node).use { stream ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val amount = stream.read(buffer)
                        if (amount < 0) break
                        digest.update(buffer, 0, amount)
                    }
                }
                val after = attrs(node)
                require(after.isRegularFile && a.size() == after.size() &&
                    a.lastModifiedTime() == after.lastModifiedTime() &&
                    (a.fileKey() == null || a.fileKey() == after.fileKey())) {
                    "Mod contents changed during review" }
            }
        }
        walk(directory, "", 0)
        return hex(digest.digest())
    }

    private fun rootWitness(canonicalRoot: File): String {
        val a = attrs(modsDir)
        require(a.isDirectory && !a.isSymbolicLink) { "Mods root changed" }
        val names = requireNotNull(modsDir.listFiles()) { "Cannot inspect Mods contents" }
        val digest = sha()
        digest.text(canonicalRoot.path)
        digest.text(a.fileKey()?.toString().orEmpty())
        names.sortedBy { it.name }.forEach { file ->
            val state = attrs(file)
            require(!state.isSymbolicLink && !state.isOther) { "Linked or special mod root child" }
            digest.text("${file.name}:${state.isDirectory}:${state.isRegularFile}")
        }
        return hex(digest.digest())
    }

    /** Non-mutating preflight. A metadata fingerprint is NOT a filesystem witness. */
    fun review(moves: List<ProfileFolderMove>, inventoryFingerprint: String): BulkFolderReview =
        synchronized(processLock) {
            check(!exists(journal)) { "Unresolved bulk transaction" }
            require(inventoryFingerprint.length == 64 && inventoryFingerprint.all {
                it in "0123456789abcdef" }) { "Invalid inventory fingerprint" }
            val root = root()
            val sources = validateMoves(moves, root)
            val sourceHashes = sources.map(::treeHash)
            val witness = rootWitness(root)
            BulkFolderReview(UUID.randomUUID().toString(), inventoryFingerprint, witness,
                moves.toList(), sourceHashes.toList())
        }

    private fun compareReview(review: BulkFolderReview) {
        require(review.identity !in usedTokens) { "Approval was already consumed" }
        val root = root()
        val sources = validateMoves(review.moves, root)
        check(rootWitness(root) == review.rootWitness &&
            sources.map(::treeHash) == review.sourceHashes) {
            "Filesystem changed since review" }
    }

    private fun store(plan: BulkFolderReview) {
        check(!exists(journal)) { "Unresolved bulk transaction" }
        check(privateRoot.isDirectory || privateRoot.mkdirs()) { "Private journal inaccessible" }
        require(PlatformStoragePaths.inspect(privateRoot).safe &&
            !Files.isSymbolicLink(privateRoot.toPath())) { "Unsafe private journal root" }
        val props = Properties().apply {
            setProperty("schema", "1")
            setProperty("root", root().path)
            setProperty("root_witness", plan.rootWitness)
            setProperty("count", plan.moves.size.toString())
            plan.moves.forEachIndexed { i, move ->
                setProperty("from.$i", move.from)
                setProperty("to.$i", move.to)
                setProperty("hash.$i", plan.sourceHashes[i])
            }
        }
        val temp = File(privateRoot, ".m25-bulk-${UUID.randomUUID()}.tmp")
        try {
            FileOutputStream(temp).use { output ->
                props.store(output, "Rollback-only mod folder journal")
                output.fd.sync()
            }
            check(temp.renameTo(journal)) { "Bulk journal publish refused" }
            check(journal.isFile && !Files.isSymbolicLink(journal.toPath())) {
                "Bulk journal witness unavailable" }
        } finally {
            if (exists(temp)) temp.delete()
        }
    }

    private fun readJournal(): Pair<List<ProfileFolderMove>, List<String>>? {
        val props = runCatching { Properties().apply { journal.inputStream().use { load(it) } } }
            .getOrNull() ?: return null
        if (props.getProperty("schema") != "1" ||
            props.getProperty("root") != runCatching { root().path }.getOrNull()) return null
        val witness = props.getProperty("root_witness") ?: return null
        if (witness.length != 64 || witness.any { it !in "0123456789abcdef" }) return null
        val count = props.getProperty("count")?.toIntOrNull() ?: return null
        if (count !in 1..MAX_STEPS) return null
        val keys = setOf("schema", "root", "root_witness", "count") +
            (0 until count).flatMap { listOf("from.$it", "to.$it", "hash.$it") }
        if (props.stringPropertyNames() != keys.toSet()) return null
        val moves = (0 until count).map { i ->
            ProfileFolderMove(props.getProperty("from.$i") ?: return null,
                props.getProperty("to.$i") ?: return null)
        }
        val hashes = (0 until count).map { i ->
            (props.getProperty("hash.$i") ?: return null).also {
                if (it.length != 64 || it.any { c -> c !in "0123456789abcdef" }) return null
            }
        }
        // Validate names and conflicts without demanding all sources exist (some have moved).
        val root = runCatching { root() }.getOrNull() ?: return null
        if (runCatching {
            require(moves.map { it.from.lowercase(Locale.ROOT) }.distinct().size == moves.size)
            require(moves.map { it.to.lowercase(Locale.ROOT) }.distinct().size == moves.size)
            require(moves.map { it.from.lowercase(Locale.ROOT) }.toSet().intersect(
                moves.map { it.to.lowercase(Locale.ROOT) }.toSet()).isEmpty())
            moves.forEach { m ->
                child(m.from, root); child(m.to, root)
                require(m.from != m.to &&
                    (if (m.from.startsWith('.')) m.from.drop(1) == m.to
                     else ".${m.from}" == m.to))
            }
        }.isFailure) return null
        return moves to hashes
    }

    /** Fail closed on a modified file, collision, unreadable folder, or suspicious path. */
    fun recover(): Boolean = synchronized(processLock) {
        if (!exists(journal)) return@synchronized true
        if (!PlatformStoragePaths.inspect(privateRoot).safe ||
            !journal.isFile || Files.isSymbolicLink(journal.toPath())) return@synchronized false
        val (moves, hashes) = readJournal() ?: return@synchronized false
        val canonicalRoot = runCatching { root() }.getOrNull() ?: return@synchronized false
        // Pre-verify the ENTIRE transaction before touching anything.
        val moved = mutableListOf<Boolean>()
        for ((i, move) in moves.withIndex()) {
            val source = runCatching { child(move.from, canonicalRoot) }.getOrNull()
                ?: return@synchronized false
            val target = runCatching { child(move.to, canonicalRoot) }.getOrNull()
                ?: return@synchronized false
            val old = exists(source)
            val new = exists(target)
            if (old == new) return@synchronized false
            val present = if (old) source else target
            if (!present.isDirectory || runCatching { treeHash(present) }.getOrNull() != hashes[i])
                return@synchronized false
            moved += new
        }
        for (i in moves.indices.reversed()) {
            if (!moved[i]) continue
            val move = moves[i]
            val source = runCatching { child(move.from, canonicalRoot) }.getOrNull()
                ?: return@synchronized false
            val target = runCatching { child(move.to, canonicalRoot) }.getOrNull()
                ?: return@synchronized false
            if (exists(source) || !target.renameTo(source)) return@synchronized false
        }
        for ((i, move) in moves.withIndex()) {
            if (runCatching { treeHash(child(move.from, canonicalRoot)) }.getOrNull() != hashes[i])
                return@synchronized false
        }
        return@synchronized journal.delete() || !exists(journal)
    }

    /** Tests can prepare and simulate real process death without catching an injected exception. */
    internal fun prepare(review: BulkFolderReview) = synchronized(processLock) {
        check(recover()) { "Bulk recovery ambiguous; manual inspection required" }
        compareReview(review)
        store(review)
    }

    /** Only callable by future explicitly qualified integration; NEVER loop single-mod toggles. */
    fun apply(review: BulkFolderReview, currentInventoryFingerprint: String): Int =
        synchronized(processLock) {
            check(recover()) { "Bulk recovery ambiguous; manual inspection required" }
            check(review.inventoryFingerprint == currentInventoryFingerprint) {
                "Stale mod inventory" }
            compareReview(review)
            store(review)
            usedTokens.add(review.identity)
            try {
                val canonicalRoot = root()
                review.moves.forEachIndexed { i, move ->
                    val source = child(move.from, canonicalRoot)
                    val target = child(move.to, canonicalRoot)
                    check(source.isDirectory && !exists(target) &&
                        treeHash(source) == review.sourceHashes[i]) { "Mod changed during commit" }
                    check(source.renameTo(target)) { "Mod folder rename failed" }
                    check(treeHash(target) == review.sourceHashes[i]) { "Mod bytes changed during move" }
                }
                check(journal.delete()) { "Could not finalize mod bulk journal" }
                review.moves.size
            } catch (failure: Exception) {
                check(recover()) { "MANUAL_REVIEW_REQUIRED: bulk rollback could not be proven" }
                throw IllegalStateException("Bulk operation refused; original mod bytes restored", failure)
            }
        }
}
