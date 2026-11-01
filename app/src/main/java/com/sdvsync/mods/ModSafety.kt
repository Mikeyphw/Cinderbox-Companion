package com.sdvsync.mods

import java.io.File
import com.sdvsync.local.PlatformStoragePaths
import java.nio.file.Files
import java.security.MessageDigest
import java.util.Properties
import java.util.UUID

/** A review is bound to the *bytes* of the archive, not merely its filename. */
data class ModReviewChange(
    val modName: String,
    val uniqueId: String,
    val folder: String,
    val action: String,
    val added: Int,
    val replaced: Int,
    val removed: Int
)

data class ModArchivePreview(val sha256: String, val changes: List<ModReviewChange>,
                             val existingDigest: String = "") {
    val approvalKey: String get() = sha256 + ":" + existingDigest + ":" + changes.joinToString("|") {
        "${it.uniqueId}:${it.folder}:${it.action}:${it.added}:${it.replaced}:${it.removed}"
    }
}

data class ModSnapshot(val id: String, val folder: String, val createdAt: Long)

/** File-system safety operations use app-private durable metadata and immutable snapshots. */
internal class ModSafety(private val privateRoot: File, private val modsDir: File) {
    private val backupRoot get() = File(privateRoot, "mod-snapshots")
    private val journal get() = File(privateRoot, "mod-operation.properties")

    private fun validateName(name: String) {
        require(name.isNotBlank() && name != "." && name != ".." &&
            '/' !in name && '\\' !in name && '\u0000' !in name) { "Invalid mod folder name" }
    }

    private fun ensureNoLinks(root: File) {
        require(PlatformStoragePaths.inspect(root).safe) { "Mod path includes an unsafe symlink" }
        if (root.exists()) {
            root.walkTopDown().forEach { file ->
                require(!Files.isSymbolicLink(file.toPath())) { "Snapshot contains a symlink" }
            }
        }
    }

    fun digest(file: File): String {
        val hash = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val size = input.read(buffer)
                if (size < 0) break
                hash.update(buffer, 0, size)
            }
        }
        return hash.digest().joinToString("") { "%02x".format(it) }
    }

    fun snapshot(folder: File): ModSnapshot? {
        validateName(folder.name)
        if (!folder.exists()) return null
        check(folder.isDirectory) { "Mod replacement target is not a directory" }
        ensureNoLinks(folder)
        check(backupRoot.mkdirs() || backupRoot.isDirectory) { "Cannot create retained mod backup directory" }
        val id = UUID.randomUUID().toString()
        val staging = File(backupRoot, ".$id.tmp")
        val destination = File(backupRoot, id)
        check(staging.mkdir()) { "Cannot stage mod snapshot" }
        try {
            val data = File(staging, "files")
            check(folder.copyRecursively(data, overwrite = false)) { "Mod snapshot copy failed" }
            val metadata = Properties().apply {
                setProperty("folder", folder.name)
                setProperty("created_at", System.currentTimeMillis().toString())
            }
            File(staging, "snapshot.properties").outputStream().use { metadata.store(it, "Mod snapshot") }
            check(staging.renameTo(destination)) { "Cannot commit retained mod snapshot" }
            return ModSnapshot(id, folder.name, metadata.getProperty("created_at").toLong())
        } finally {
            if (staging.exists()) staging.deleteRecursively()
        }
    }

    fun list(): List<ModSnapshot> = backupRoot.listFiles()?.filter { it.isDirectory &&
        Regex("[0-9a-f-]{36}").matches(it.name) && File(it, "files").isDirectory &&
        File(it, "snapshot.properties").isFile
    }?.mapNotNull { item ->
        runCatching {
            val data = Properties().apply {
                File(item, "snapshot.properties").inputStream().use { load(it) }
            }
            val folder = data.getProperty("folder") ?: return@runCatching null
            validateName(folder)
            ModSnapshot(item.name, folder, data.getProperty("created_at").toLong())
        }.getOrNull()
    }?.sortedByDescending { it.createdAt } ?: emptyList()

    fun begin(folder: String, snapshot: ModSnapshot?, operation: String) {
        check(!journal.exists()) { "Unresolved mod transaction; reopen Mods to recover it" }
        validateName(folder)
        check(privateRoot.isDirectory || privateRoot.mkdirs()) { "Mod journal storage unavailable" }
        val props = Properties().apply {
            setProperty("folder", folder)
            setProperty("snapshot", snapshot?.id ?: "")
            setProperty("operation", operation)
        }
        val temp = File(privateRoot, "mod-operation.tmp")
        temp.outputStream().use { props.store(it, "Interrupted mod operation recovery") }
        check(temp.renameTo(journal)) { "Cannot commit mod operation journal" }
    }

    fun complete() {
        check(journal.delete() || !journal.exists()) { "Cannot clear mod operation journal" }
    }

    /** Only automatic recovery of a *missing* target; ambiguity is never deleted. */
    fun recover(): Boolean {
        if (!journal.exists()) return true
        val data = Properties().apply { journal.inputStream().use { load(it) } }
        val name = data.getProperty("folder") ?: return false
        runCatching { validateName(name) }.getOrElse { return false }
        val target = File(modsDir, name)
        // An initial install has no prior snapshot. Its journal is ambiguous after a crash:
        // neither a missing target nor an unrecognized existing directory proves success.
        // Keep the journal and block further modifications until explicitly reviewed.
        val id = data.getProperty("snapshot")?.takeIf { Regex("[0-9a-f-]{36}").matches(it) }
            ?: return false
        // The journal must name an actual retained snapshot for this same folder.
        // A syntactically valid ID (or another mod's snapshot) proves nothing.
        if (list().none { it.id == id && it.folder == name }) return false
        val previous = File(backupRoot, "$id/files")
        if (!previous.isDirectory) return false
        if (runCatching { ensureNoLinks(previous) }.isFailure) return false
        if (target.exists()) {
            // An existing mod is safe to leave alone, not automatically overwrite.
            if (runCatching { ensureNoLinks(target) }.isFailure) return false
            return target.isDirectory && File(target, "manifest.json").isFile &&
                runCatching { complete() }.isSuccess
        }
        val stage = File(modsDir, ".m5-recover-${UUID.randomUUID()}")
        if (!previous.copyRecursively(stage, overwrite = false)) return false
        if (!stage.renameTo(target)) return false
        complete()
        return true
    }

    fun restore(id: String): Boolean {
        require(Regex("[0-9a-f-]{36}").matches(id)) { "Invalid snapshot identifier" }
        check(recover()) { "Unresolved previous mod operation" }
        val backup = list().firstOrNull { it.id == id } ?: return false
        val source = File(backupRoot, "$id/files")
        ensureNoLinks(source)
        val target = File(modsDir, backup.folder)
        ensureNoLinks(target)
        val current = snapshot(target) // Restore must itself be reversible.
        val stage = File(modsDir, ".m5-restore-${UUID.randomUUID()}")
        check(source.copyRecursively(stage, overwrite = false)) { "Could not prepare restore" }
        val hold = File(modsDir, ".m5-hold-${UUID.randomUUID()}")
        begin(target.name, current, "restore")
        try {
            if (target.exists()) check(target.renameTo(hold)) { "Cannot move existing mod aside" }
            check(stage.renameTo(target)) { "Cannot activate restored mod" }
            complete()
            if (hold.exists()) hold.deleteRecursively()
            return true
        } catch (failure: Exception) {
            if (!target.exists() && hold.exists()) hold.renameTo(target)
            throw failure
        } finally {
            if (stage.exists()) stage.deleteRecursively()
        }
    }
}

/** Single durable pending review. Downloads are NEVER installed before user approval. */
internal class ModReviewQueue(private val root: File) {
    companion object { private val queueLock = Any() }
    private val pending get() = File(root, "mod-review-pending.zip")
    private val metadata get() = File(root, "mod-review-pending.properties")

    fun hasPending(): Boolean = pending.exists() || metadata.exists()
    fun archive(): File? = pending.takeIf { it.isFile }
    fun description(): String {
        if (!hasPending()) return ""
        return runCatching { Properties().apply {
            if (metadata.isFile) metadata.inputStream().use { load(it) }
        }.getProperty("name") ?: "Mod archive" }.getOrDefault("Mod archive")
    }
    fun source(): Pair<String, String> {
        val props = Properties()
        if (metadata.isFile) metadata.inputStream().use { props.load(it) }
        return (props.getProperty("source") ?: "local") to (props.getProperty("mod_id") ?: "")
    }
    fun enqueue(file: File, name: String, source: String, modId: String) = synchronized(queueLock) {
        check(!hasPending() && !pending.exists() && !metadata.exists()) {
            "A mod archive is already awaiting review in Mods"
        }
        check(root.isDirectory || root.mkdirs()) { "Cannot access pending review storage" }
        require(file.isFile && file.length() in 1..1_073_741_824L) { "Invalid mod archive size" }
        val stage = File(root, "mod-review-staging.zip")
        check(file.copyTo(stage, overwrite = false).length() == file.length()) { "Cannot stage mod review" }
        try {
            val props = Properties().apply {
                setProperty("name", name.take(150)); setProperty("source", source.take(50));
                setProperty("mod_id", modId.take(100))
            }
            val tempProps = File(root, "mod-review-pending.tmp")
            tempProps.outputStream().use { props.store(it, "Pending mod review") }
            check(stage.renameTo(pending)) { "Cannot publish queued mod" }
            check(tempProps.renameTo(metadata)) { "Cannot publish mod review metadata" }
        } finally { if (stage.exists()) stage.delete() }
    }
    fun clear() = synchronized(queueLock) {
        check(pending.delete() || !pending.exists())
        check(metadata.delete() || !metadata.exists())
    }
}
