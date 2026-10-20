package com.sdvsync.download

import java.security.MessageDigest

/** Bound PICS appinfo depot manifest IDs. A manifest ID is NOT a depot file hash,
 * Steam depot entitlement, a signature, or a proof of downloaded bytes.
 */
object M24DepotManifestIdentity {
    private val digestPattern = Regex("[0-9a-f]{64}")
    private val branchPattern = Regex("[A-Za-z0-9_.-]{1,128}")

    data class Snapshot(val branch: String, val buildId: Long, val depotCount: Int, val fingerprint: String)

    /** Metadata must be obtained from a fresh PICS appinfo response, not from
     * files, the download callback, or a locally stored integrity ledger.
     */
    fun snapshot(branch: String, buildId: Long, manifestIds: Map<Int, String>): Snapshot {
        require(branchPattern.matches(branch) && buildId > 0L) { "Invalid Steam PICS branch identity" }
        require(manifestIds.size in 1..128) { "Steam depot manifest identity unavailable" }
        require(manifestIds.keys.all { it > 0 } &&
            manifestIds.values.all { it.matches(Regex("[0-9]{1,20}")) && it.any { c -> c != '0' } }) {
            "Invalid Steam depot manifest ID"
        }
        // Length-delimited/canonical representation: no locale, path or JSON ambiguity.
        val canonical = buildString {
            append("M24-PICS-DEPOT-MANIFEST-IDS\n413150\n")
            append(branch.length).append(':').append(branch).append('\n')
            append(buildId).append('\n')
            manifestIds.toSortedMap().forEach { (id, manifest) ->
                append(id).append(':').append(manifest.length).append(':').append(manifest).append('\n')
            }
        }
        val hash = MessageDigest.getInstance("SHA-256")
            .digest(canonical.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
        return Snapshot(branch, buildId, manifestIds.size, hash)
    }

    fun requireMatching(fingerprint: String?, observed: Snapshot) {
        check(fingerprint != null && digestPattern.matches(fingerprint) &&
            fingerprint == observed.fingerprint) {
            "Steam PICS depot manifest set changed or was not bound; staged bytes preserved"
        }
    }
}
