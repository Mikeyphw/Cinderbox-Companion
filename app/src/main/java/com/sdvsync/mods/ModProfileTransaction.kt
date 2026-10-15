package com.sdvsync.mods

import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.LinkOption
import java.util.Properties
import java.util.UUID

/** One direct-child folder rename; names are never interpreted as paths. */
internal data class ProfileFolderMove(val from: String, val to: String)

/**
 * A durable, rollback-only journal for M7 profiles. Nothing is deleted or overwritten.
 * After process death, a new manager reverses completed renames before reading Mods.
 * Ambiguous directory states keep the journal in place and block further mutations.
 */
internal class ModProfileTransaction(private val privateRoot: File, private val modsDir: File) {
    private val journal get() = File(privateRoot, "m8-profile-transaction.properties")
    private fun exists(file: File): Boolean = Files.exists(file.toPath(), LinkOption.NOFOLLOW_LINKS)

    private fun safe(name: String): File {
        require(name.isNotBlank() && name != "." && name != ".." &&
            '/' !in name && '\\' !in name && '\u0000' !in name) { "Invalid profile folder name" }
        // Reject symlink components, including a replacement of the Mods root.
        var part: File? = modsDir.absoluteFile
        while (part != null) {
            require(!Files.isSymbolicLink(part.toPath())) { "Mods path is a symlink" }
            part = part.parentFile
        }
        val child = File(modsDir, name)
        require(!Files.isSymbolicLink(child.toPath())) { "Mod folder is a symlink" }
        require(child.canonicalFile.parentFile == modsDir.canonicalFile) { "Mod path escaped Mods" }
        return child
    }

    private fun validateNames(moves: List<ProfileFolderMove>) {
        require(moves.isNotEmpty() && moves.size <= 512) { "Invalid profile transaction length" }
        val sources = moves.map { safe(it.from); it.from }
        val targets = moves.map { safe(it.to); it.to }
        require(sources.size == sources.toSet().size && targets.size == targets.toSet().size &&
            sources.toSet().intersect(targets.toSet()).isEmpty() &&
            moves.none { it.from == it.to }) { "Conflicting profile rename paths" }
    }

    private fun load(): List<ProfileFolderMove>? {
        val props = runCatching { Properties().apply { journal.inputStream().use { load(it) } } }
            .getOrNull() ?: return null
        if (props.getProperty("schema") != "1" ||
            props.getProperty("mods_root") != modsDir.canonicalPath) return null
        val count = props.getProperty("count")?.toIntOrNull() ?: return null
        if (count !in 1..512) return null
        if (props.stringPropertyNames() != (setOf("schema", "mods_root", "count") +
                (0 until count).flatMap { listOf("from.$it", "to.$it") }).toSet()) return null
        val moves = (0 until count).map { i ->
            ProfileFolderMove(props.getProperty("from.$i") ?: return null,
                props.getProperty("to.$i") ?: return null)
        }
        if (runCatching { validateNames(moves) }.isFailure) return null
        return moves
    }

    /** Commit journal before the first rename. Also useful for process-death tests. */
    @Synchronized internal fun prepare(moves: List<ProfileFolderMove>) {
        check(!exists(journal)) { "A mod profile recovery is pending" }
        validateNames(moves)
        for (move in moves) {
            val source = safe(move.from)
            val target = safe(move.to)
            check(source.isDirectory && !exists(target)) { "Profile rename collision" }
        }
        check(privateRoot.isDirectory || privateRoot.mkdirs()) { "Profile journal directory inaccessible" }
        val props = Properties().apply {
            setProperty("schema", "1")
            setProperty("mods_root", modsDir.canonicalPath)
            setProperty("count", moves.size.toString())
            moves.forEachIndexed { i, step ->
                setProperty("from.$i", step.from)
                setProperty("to.$i", step.to)
            }
        }
        val temp = File(privateRoot, ".m8-profile-${UUID.randomUUID()}.tmp")
        try {
            FileOutputStream(temp).use { stream ->
                props.store(stream, "Crash-safe profile rollback; no contents or tokens")
                stream.fd.sync()
            }
            check(temp.renameTo(journal)) { "Could not commit mod profile journal" }
        } finally {
            if (exists(temp)) temp.delete()
        }
    }

    /** Roll back a partially or fully applied profile after an unexpected process exit. */
    @Synchronized fun recover(): Boolean {
        if (!exists(journal)) return true
        if (!journal.isFile || Files.isSymbolicLink(journal.toPath())) return false
        val moves = load() ?: return false
        // Preflight ALL entries before mutating one; corruption or collision is fail-closed.
        val states = mutableListOf<Boolean>()
        for (move in moves) {
            val from = runCatching { safe(move.from) }.getOrElse { return false }
            val to = runCatching { safe(move.to) }.getOrElse { return false }
            val f = exists(from)
            val t = exists(to)
            if (f == t || (f && !from.isDirectory) || (t && !to.isDirectory)) return false
            states.add(t)
        }
        for (i in moves.indices.reversed()) {
            if (!states[i]) continue
            val move = moves[i]
            val source = runCatching { safe(move.from) }.getOrElse { return false }
            val target = runCatching { safe(move.to) }.getOrElse { return false }
            if (exists(source) || !target.isDirectory || !target.renameTo(source)) return false
        }
        return journal.delete() || !exists(journal)
    }

    @Synchronized fun apply(moves: List<ProfileFolderMove>): Int {
        check(recover()) { "Unresolved mod profile transaction; manual recovery required" }
        if (moves.isEmpty()) return 0
        prepare(moves)
        try {
            for (move in moves) {
                val source = safe(move.from)
                val target = safe(move.to)
                check(source.isDirectory && !exists(target)) { "Profile changed during application" }
                check(source.renameTo(target)) { "Cannot rename mod profile folder" }
            }
            check(journal.delete()) { "Cannot finalize mod profile transaction" }
            return moves.size
        } catch (failure: Exception) {
            if (!recover()) {
                throw IllegalStateException("Profile recovery ambiguous; stop and inspect folders manually", failure)
            }
            throw IllegalStateException("Profile change rejected; original folder states restored", failure)
        }
    }
}
