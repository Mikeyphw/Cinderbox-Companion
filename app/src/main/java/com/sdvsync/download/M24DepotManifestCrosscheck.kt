package com.sdvsync.download

import `in`.dragonbra.javasteam.depotdownloader.Util
import `in`.dragonbra.javasteam.enums.EDepotFileFlag
import java.io.File
import okio.Path.Companion.toPath

/** Reads JavaSteam's depot manifests and checks bytes; cached .sha is a local
 * checksum, NOT a Valve signature. PICS IDs are a separate live-session binding.
 */
object M24DepotManifestCrosscheck {
    fun verify(stage: File, picsIds: Map<Int, String>, completedDepots: Set<Int>? = null,
               progress: (Int, Int) -> Unit = { _, _ -> }): M24DepotFileProof.Result {
        require(picsIds.isNotEmpty() && picsIds.size <= 128) { "Missing live PICS manifest identities" }
        val expected = LinkedHashMap<String, M24DepotFileProof.FileEntry>()
        val config = File(stage, ".DepotDownloader")
        require(config.isDirectory && !java.nio.file.Files.isSymbolicLink(config.toPath())) {
            "Missing SDK depot manifests"
        }
        // PICS includes Windows, macOS, Linux and language-specific depots.
        // New transfers must supply SDK-confirmed completed depots. Post-crash
        // reconciliation may infer them only from a matching cached manifest;
        // it never claims proof of entitlement or a complete app/depot inventory.
        val selected = if (completedDepots != null) {
            require(completedDepots.isNotEmpty() && completedDepots.size <= 128) {
                "No bounded completed depot list to verify; staged bytes preserved"
            }
            val missing = (completedDepots - picsIds.keys).sorted()
            check(missing.isEmpty()) {
                "PICS manifest ID missing for completed depot(s) ${missing.joinToString(",")}; " +
                    "downloaded bytes and checkpoint preserved"
            }
            completedDepots
        } else {
            picsIds.filter { (id, gid) ->
                id > 0 && gid.matches(Regex("[0-9]{1,20}")) &&
                    File(config, "${id}_${gid}.manifest").isFile
            }.keys
        }
        require(selected.isNotEmpty()) { "No completed or recoverable depots to verify" }
        for (depot in selected.sorted()) {
            val gidString = checkNotNull(picsIds[depot])

            require(depot > 0 && gidString.matches(Regex("[0-9]{1,20}"))) { "Invalid PICS depot ID" }
            val gid = gidString.toULongOrNull()?.takeIf { it > 0UL && it <= Long.MAX_VALUE.toULong() }
                ?: error("Depot manifest ID out of range")
            val manifest = Util.loadManifestFromFile(config.absolutePath.toPath(), depot, gid.toLong(), true)
                ?: error("Expected depot manifest unavailable or corrupt")
            check(manifest.depotID == depot && manifest.manifestGID == gid.toLong() && !manifest.filenamesEncrypted) {
                "Cached depot manifest identity mismatch or encrypted filenames"
            }
            for (file in manifest.files) {
                if (file.flags.contains(EDepotFileFlag.Directory)) continue
                check(file.linkTarget.isNullOrBlank()) { "Manifest contains file link" }
                val name = M24DepotFileProof.checkedPath(file.fileName.replace('\\', '/'))
                require(!name.startsWith(".DepotDownloader/")) { "Manifest includes SDK state" }
                val hash = file.fileHash
                require(hash.size == 20) { "Depot manifest missing SHA-1" }
                val entry = M24DepotFileProof.FileEntry(file.totalSize,
                    hash.joinToString("") { "%02x".format(it) })
                val previous = expected.putIfAbsent(name, entry)
                require(previous == null || previous == entry) { "Conflicting depot files" }
            }
        }
        return M24DepotFileProof.verify(stage, expected, progress)
    }
}
