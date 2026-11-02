package com.sdvsync.mods

import java.io.File
import com.sdvsync.local.PlatformStoragePaths
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.Properties
import java.util.UUID

/** A validated extracted mod folder, destined for exactly one Mods/ direct child. */
internal data class BatchModEntry(val targetName: String, val sourceFolder: File)

/**
 * Journaled all-or-rollback ZIP installation. All incoming files are staged on the Mods
 * filesystem first; replaced folders are renamed into the transaction workspace.
 * A process death before final journal removal always means ROLLBACK, never partial commit.
 * Unknown content, symlinks and collisions leave the journal intact for manual recovery.
 */
internal class ModBatchTransaction(private val privateRoot: File, private val modsDir: File) {
    private val journal get() = File(privateRoot, "m9-mod-batch.properties")
    private data class Step(val name: String, val hadOriginal: Boolean, val oldHash: String,
                            val newHash: String)
    private data class Plan(val workspace: File, val steps: List<Step>)
    private enum class State { UNTOUCHED, HELD, PUBLISHED, ABSENT, ADDED }

    private fun exists(file: File) = Files.exists(file.toPath(), LinkOption.NOFOLLOW_LINKS)
    private fun safeRoot() {
        require(PlatformStoragePaths.inspect(modsDir).safe) { "Mods path contains an unsafe symbolic link" }
        require(!exists(modsDir) || modsDir.isDirectory) { "Mods folder unavailable" }
    }
    private fun safeName(name: String): File {
        require(name.isNotBlank() && name != "." && name != ".." &&
            '/' !in name && '\\' !in name && '\u0000' !in name &&
            !name.startsWith(".m9-batch-")) { "Unsafe mod folder name" }
        safeRoot()
        val child = File(modsDir, name)
        require(!Files.isSymbolicLink(child.toPath()) &&
            child.canonicalFile.parentFile == modsDir.canonicalFile) { "Unsafe mod folder path" }
        return child
    }
    private fun cleanTree(directory: File) {
        require(directory.isDirectory && !Files.isSymbolicLink(directory.toPath())) { "Unsafe mod tree" }
        directory.walkTopDown().onEnter { folder ->
            require(!Files.isSymbolicLink(folder.toPath())) { "Symlink in mod tree" }
            true
        }.forEach { require(!Files.isSymbolicLink(it.toPath())) { "Symlink in mod tree" } }
    }
    /** Content and path fingerprint; reject an edited mod rather than delete someone else's data. */
    private fun treeHash(folder: File): String {
        cleanTree(folder)
        val digest = MessageDigest.getInstance("SHA-256")
        val files = folder.walkTopDown().filter { it != folder }.toList().sortedBy {
            it.relativeTo(folder).invariantSeparatorsPath
        }
        for (file in files) {
            val name = file.relativeTo(folder).invariantSeparatorsPath.toByteArray(Charsets.UTF_8)
            digest.update(name.size.toString().toByteArray(Charsets.US_ASCII)); digest.update(0)
            digest.update(name); digest.update(0)
            digest.update(if (file.isDirectory) 1 else 2)
            if (file.isFile) file.inputStream().buffered().use { stream ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val n = stream.read(buffer)
                    if (n < 0) break
                    digest.update(buffer, 0, n)
                }
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
    /** Bind approvals to the actual installed bytes, not only ZIP bytes and file counts. */
    internal fun destinationFingerprint(names: List<String>): String {
        val md = MessageDigest.getInstance("SHA-256")
        for (name in names.sorted()) {
            val target = safeName(name)
            val value = when {
                !exists(target) -> "absent"
                target.isDirectory -> treeHash(target)
                else -> error("Conflicting mod destination")
            }
            md.update(name.toByteArray(Charsets.UTF_8))
            md.update(0)
            md.update(value.toByteArray(Charsets.US_ASCII))
            md.update(0)
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
    private fun stageFolder(work: File, i: Int) = File(work, "incoming/$i")
    private fun originalFolder(work: File, i: Int) = File(work, "original/$i")
    private fun parse(): Plan? {
        if (!journal.isFile || Files.isSymbolicLink(journal.toPath()) ||
            journal.length() !in 1..262144) return null
        val props = runCatching { Properties().apply { journal.inputStream().use { load(it) } } }.getOrNull()
            ?: return null
        if (props.getProperty("schema") != "1" ||
            props.getProperty("mods_root") != modsDir.canonicalPath) return null
        val id = props.getProperty("id") ?: return null
        if (!Regex("[0-9a-f-]{36}").matches(id)) return null
        val count = props.getProperty("count")?.toIntOrNull() ?: return null
        if (count !in 1..256) return null
        val names = (0 until count).flatMap { listOf("target.$it", "had.$it", "old.$it", "new.$it") }
        if (props.stringPropertyNames() != (setOf("schema", "mods_root", "id", "count") + names)) return null
        val steps = (0 until count).map { i ->
            val name = props.getProperty("target.$i") ?: return null
            val had = when (props.getProperty("had.$i")) { "true" -> true; "false" -> false; else -> return null }
            val old = props.getProperty("old.$i") ?: return null
            val new = props.getProperty("new.$i") ?: return null
            if (runCatching { safeName(name) }.isFailure ||
                !Regex("[0-9a-f]{64}").matches(new) ||
                (had && !Regex("[0-9a-f]{64}").matches(old)) || (!had && old.isNotEmpty())) return null
            Step(name, had, old, new)
        }
        if (steps.map { it.name.lowercase(java.util.Locale.ROOT) }.toSet().size != count) return null
        val work = File(modsDir, ".m9-batch-$id")
        if (!work.isDirectory || Files.isSymbolicLink(work.toPath()) ||
            work.canonicalFile.parentFile != modsDir.canonicalFile) return null
        return Plan(work, steps)
    }
    private fun state(plan: Plan, i: Int): State? {
        val step = plan.steps[i]
        val target = runCatching { safeName(step.name) }.getOrElse { return null }
        val incoming = stageFolder(plan.workspace, i)
        val held = originalFolder(plan.workspace, i)
        val t = exists(target); val n = exists(incoming); val h = exists(held)
        if ((t && !target.isDirectory) || (n && !incoming.isDirectory) ||
            (h && !held.isDirectory)) return null
        val hashesMatch = runCatching {
            if (n && treeHash(incoming) != step.newHash) return null
            if (h && (!step.hadOriginal || treeHash(held) != step.oldHash)) return null
            true
        }.getOrElse { return null }
        if (!hashesMatch) return null
        if (step.hadOriginal) {
            return when {
                t && n && !h && treeHash(target) == step.oldHash -> State.UNTOUCHED
                !t && n && h -> State.HELD
                t && !n && h && treeHash(target) == step.newHash -> State.PUBLISHED
                else -> null
            }
        }
        return when {
            !t && n && !h -> State.ABSENT
            t && !n && !h && treeHash(target) == step.newHash -> State.ADDED
            else -> null
        }
    }
    /** Recovery is idempotent across further process deaths during rollback. */
    @Synchronized fun recover(): Boolean {
        if (!exists(journal)) return true
        val plan = runCatching { parse() }.getOrNull() ?: return false
        // Validate ALL destinations, workspace payloads and hashes before touching any folder.
        val states = runCatching { plan.steps.indices.map { state(plan, it) ?: return false } }
            .getOrElse { return false }
        for (i in plan.steps.indices.reversed()) {
            val step = plan.steps[i]
            val target = runCatching { safeName(step.name) }.getOrElse { return false }
            val incoming = stageFolder(plan.workspace, i)
            val held = originalFolder(plan.workspace, i)
            when (states[i]) {
                State.PUBLISHED -> {
                    if (!target.renameTo(incoming) || !held.renameTo(target)) return false
                }
                State.HELD -> if (!held.renameTo(target)) return false
                State.ADDED -> if (!target.renameTo(incoming)) return false
                State.UNTOUCHED, State.ABSENT -> Unit
            }
        }
        // A failed cleanup never causes the workspace to be treated as another installed mod.
        if (!journal.delete() && exists(journal)) return false
        runCatching { plan.workspace.deleteRecursively() }
        return true
    }
    @Synchronized fun install(entries: List<BatchModEntry>, snapshot: (File) -> Unit,
                              expectedExistingDigest: String? = null,
                              afterStep: (Int) -> Unit = {}): Int {
        check(recover()) { "Unresolved multi-mod transaction; manual recovery required" }
        require(entries.isNotEmpty() && entries.size <= 256) { "Invalid mod batch size" }
        check(!exists(journal)) { "Mod batch recovery pending" }
        check(modsDir.isDirectory || modsDir.mkdirs()) { "Mods destination inaccessible" }
        val names = entries.map { it.targetName.lowercase(java.util.Locale.ROOT) }
        require(names.size == names.toSet().size) { "Duplicate mod destination folders" }
        if (expectedExistingDigest != null) check(
            destinationFingerprint(entries.map { it.targetName }) == expectedExistingDigest
        ) { "Installed mod files changed after approval" }
        val targets = entries.map { entry ->
            val target = safeName(entry.targetName)
            check(!exists(target) || target.isDirectory) { "Existing mod target is not a directory" }
            if (exists(target)) cleanTree(target)
            cleanTree(entry.sourceFolder)
            target
        }
        val uuid = UUID.randomUUID().toString()
        val workspace = File(modsDir, ".m9-batch-$uuid")
        check(workspace.mkdir()) { "Cannot create mod batch workspace" }
        var journalPublished = false
        try {
            val steps = entries.mapIndexed { i, entry ->
                val incoming = stageFolder(workspace, i)
                check(incoming.parentFile.mkdirs() || incoming.parentFile.isDirectory)
                check(entry.sourceFolder.copyRecursively(incoming, overwrite = false)) { "Failed to stage mod" }
                cleanTree(incoming)
                val existing = targets[i]
                val had = exists(existing)
                val originalHash = if (had) treeHash(existing) else ""
                if (had) {
                    val config = File(existing, "config.json")
                    if (config.isFile) {
                        require(!Files.isSymbolicLink(config.toPath())) { "Unsafe mod config file" }
                        config.copyTo(File(incoming, "config.json"), overwrite = true)
                    }
                    snapshot(existing) // Retained M5 snapshot BEFORE any installed mod changes.
                    check(treeHash(existing) == originalHash) { "Existing mod changed during snapshot" }
                }
                Step(entry.targetName, had, originalHash, treeHash(incoming))
            }
            if (expectedExistingDigest != null) check(
                destinationFingerprint(entries.map { it.targetName }) == expectedExistingDigest
            ) { "Installed mod files changed while staging; review again" }
            check(privateRoot.isDirectory || privateRoot.mkdirs()) { "Private journal storage unavailable" }
            val props = Properties().apply {
                setProperty("schema", "1")
                setProperty("mods_root", modsDir.canonicalPath)
                setProperty("id", uuid)
                setProperty("count", steps.size.toString())
                steps.forEachIndexed { i, step ->
                    setProperty("target.$i", step.name)
                    setProperty("had.$i", step.hadOriginal.toString())
                    setProperty("old.$i", step.oldHash)
                    setProperty("new.$i", step.newHash)
                }
            }
            val temp = File(privateRoot, ".m9-batch-$uuid.tmp")
            try {
                FileOutputStream(temp).use { stream ->
                    props.store(stream, "M9 batch rollback journal; no credentials or mod contents")
                    stream.fd.sync()
                }
                try {
                    Files.move(temp.toPath(), journal.toPath(), StandardCopyOption.ATOMIC_MOVE)
                } catch (_: java.nio.file.AtomicMoveNotSupportedException) {
                    Files.move(temp.toPath(), journal.toPath())
                }
                journalPublished = true
            } finally { temp.delete() }
            for (i in steps.indices) {
                val target = safeName(steps[i].name)
                val hold = originalFolder(workspace, i)
                if (steps[i].hadOriginal) {
                    check(hold.parentFile.mkdirs() || hold.parentFile.isDirectory)
                    check(target.renameTo(hold)) { "Could not preserve original mod" }
                }
                check(stageFolder(workspace, i).renameTo(target)) { "Could not activate staged mod" }
                afterStep(i) // Controlled fault injection is used only by JVM recovery tests.
            }
            check(journal.delete()) { "Could not complete mod batch journal" }
            journalPublished = false
            runCatching { workspace.deleteRecursively() }
            return steps.size
        } catch (failure: Exception) {
            if (journalPublished) {
                check(recover()) { "Mod batch recovery ambiguous; stop and inspect folders" }
            } else {
                runCatching { workspace.deleteRecursively() }
            }
            throw IllegalStateException("Mod batch rejected; no partial installation committed", failure)
        }
    }
}
