package com.sdvsync.saves

import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.LinkOption
import java.security.MessageDigest
import java.util.Properties
import java.util.UUID
import com.sdvsync.local.StoragePlanner

/** Direct-file save restoration: staged before mutation, journaled, rollback-only on interruption. */
internal class SaveRestoreTransaction(private val privateRoot: File) {
    private val journal get() = File(privateRoot, "m11-save-restore.properties")
    private fun exists(f: File) = Files.exists(f.toPath(), LinkOption.NOFOLLOW_LINKS)

    private fun securePath(file: File) {
        require(file.isAbsolute) { "Save path must be absolute" }
        var current: File? = file.absoluteFile
        while (current != null) {
            require(!Files.isSymbolicLink(current.toPath())) { "Save path contains a symlink" }
            current = current.parentFile
        }
    }
    private fun flatFiles(root: File, allowEmpty: Boolean = false): List<File> {
        securePath(root)
        check(root.isDirectory && root.canRead()) { "Save folder cannot be read" }
        val files = root.listFiles() ?: error("Cannot list save folder")
        require((allowEmpty || files.isNotEmpty()) && files.size <= 512) { "Empty or oversized save folder" }
        for (f in files) {
            require(f.isFile && !Files.isSymbolicLink(f.toPath()) && f.canRead() && f.length() <= 512L * 1024 * 1024) {
                "Save contains an unsafe file or nested directory"
            }
        }
        return files.sortedBy { it.name }
    }
    private fun fingerprint(folder: File, allowEmpty: Boolean = false): String {
        val md = MessageDigest.getInstance("SHA-256")
        for (f in flatFiles(folder, allowEmpty)) {
            md.update(f.name.toByteArray(Charsets.UTF_8)); md.update(0.toByte())
            md.update(f.length().toString().toByteArray()); md.update(0.toByte())
            f.inputStream().buffered().use { input ->
                val buf = ByteArray(65536)
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    md.update(buf, 0, n)
                }
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    @Synchronized fun recover(): Boolean {
        if (!exists(journal)) return true
        if (!journal.isFile || Files.isSymbolicLink(journal.toPath()) || journal.length() !in 1..8192) return false
        val p = runCatching { Properties().apply { journal.inputStream().use { load(it) } } }.getOrNull() ?: return false
        if (p.stringPropertyNames() != setOf("schema", "target", "stage", "hold", "fingerprint", "original", "had_target") ||
            p.getProperty("schema") != "1") return false
        val target = File(p.getProperty("target") ?: return false)
        val stage = File(p.getProperty("stage") ?: return false)
        val hold = File(p.getProperty("hold") ?: return false)
        val expected = p.getProperty("fingerprint") ?: return false
        val original = p.getProperty("original") ?: return false
        val hadTarget = when (p.getProperty("had_target")) { "true" -> true; "false" -> false; else -> return false }
        if (!expected.matches(Regex("[0-9a-f]{64}")) ||
            (original != "absent" && !original.matches(Regex("[0-9a-f]{64}"))) ||
            (hadTarget == (original == "absent")) ||
            stage.parentFile != target.parentFile || hold.parentFile != target.parentFile ||
            !stage.name.matches(Regex("\\.m11-save-stage-[0-9a-f-]{36}")) ||
            !hold.name.matches(Regex("\\.m11-save-hold-[0-9a-f-]{36}"))) return false
        if (runCatching { securePath(target); securePath(stage); securePath(hold) }.isFailure) return false
        val t = exists(target); val s = exists(stage); val h = exists(hold)
        // No unrecognized folder is removed, and source/target content must match the recorded payload.
        if (s && runCatching { fingerprint(stage) }.getOrNull() != expected) return false
        if (h && (!hadTarget || !hold.isDirectory ||
                runCatching { fingerprint(hold, allowEmpty = true) }.getOrNull() != original)) return false
        if (h) {
            if (t) {
                if (s || runCatching { fingerprint(target) }.getOrNull() != expected) return false
                if (!target.renameTo(stage)) return false // Preserve published content until recovered.
            }
            if (!hold.renameTo(target)) return false
        } else if (hadTarget) {
            if (!t || !s) return false // Original target must still be present before first swap.
        } else if (t) {
            if (s || runCatching { fingerprint(target) }.getOrNull() != expected) return false
            if (!target.renameTo(stage)) return false // No original target: restore absence.
        }
        if (!journal.delete()) return false
        // Remove only transaction-owned, fingerprint-checked staging content.
        if (exists(stage) && runCatching { fingerprint(stage) }.getOrNull() == expected) stage.deleteRecursively()
        return true
    }

    @Synchronized fun restore(backup: File, target: File): Boolean {
        check(recover()) { "Unresolved save restore; manual inspection required" }
        val source = backup.absoluteFile
        val destination = target.absoluteFile
        securePath(source); securePath(destination)
        require(source.canonicalPath != destination.canonicalPath) { "Backup and target must differ" }
        val input = flatFiles(source)
        require(!exists(destination) || destination.isDirectory) { "Save target is not a directory" }
        val parent = destination.parentFile ?: error("No target parent")
        check(parent.isDirectory && parent.canWrite()) { "Save destination parent is inaccessible" }
        val id = UUID.randomUUID().toString()
        val stage = File(parent, ".m11-save-stage-$id")
        val hold = File(parent, ".m11-save-hold-$id")
        val hadTarget = exists(destination)
        val originalHash = if (hadTarget) fingerprint(destination, allowEmpty = true) else "absent"
        val originalBytes = if (hadTarget) flatFiles(destination, allowEmpty = true)
            .fold(0L) { total, f -> Math.addExact(total, f.length()) } else 0L
        val sourceBytes = input.fold(0L) { total, f -> Math.addExact(total, f.length()) }
        // Staging holds the original plus overlaid backup until the final swap.
        val budget = StoragePlanner.plan(parent, Math.addExact(originalBytes, sourceBytes))
        check(budget.sufficient == true) { "Insufficient capacity for save staging: ${budget.detail}" }
        check(stage.mkdir() && !exists(hold)) { "Cannot create restore staging" }
        var journaled = false
        try {
            // Preserve target-only files; restore never silently deletes unrelated save data.
            if (hadTarget) for (f in flatFiles(destination, allowEmpty = true)) f.copyTo(File(stage, f.name), overwrite = false)
            for (f in input) f.copyTo(File(stage, f.name), overwrite = true)
            val digest = fingerprint(stage)
            check(privateRoot.isDirectory || privateRoot.mkdirs()) { "Cannot write recovery journal" }
            val props = Properties().apply {
                setProperty("schema", "1"); setProperty("target", destination.path)
                setProperty("stage", stage.path); setProperty("hold", hold.path)
                setProperty("fingerprint", digest); setProperty("original", originalHash)
                setProperty("had_target", hadTarget.toString())
            }
            val temp = File(privateRoot, ".m11-journal-$id.tmp")
            try {
                FileOutputStream(temp).use { props.store(it, "M11 save restore, no credentials"); it.fd.sync() }
                check(temp.renameTo(journal)) { "Cannot commit save restore journal" }
            } finally { if (temp.exists()) temp.delete() }
            journaled = true
            if (hadTarget) check(destination.renameTo(hold)) { "Cannot stage previous save" }
            check(stage.renameTo(destination)) { "Cannot activate restored save" }
            check(journal.delete()) { "Cannot finalize save restore" }
            // Previous version is retained by SaveBackupManager before mutation.
            if (hold.exists()) hold.deleteRecursively()
            return true
        } catch (failure: Exception) {
            if (journaled) check(recover()) { "Restore interrupted; manual recovery required" }
            throw failure
        } finally {
            if (!journaled && stage.exists()) stage.deleteRecursively()
        }
    }
}
