package com.sdvsync.download

/** Only parent PICS responses tied to a live primary-app depotfromapp relation can
 * extend the verified manifest set. Never accept a cached GID as authority.
 */
object M24SharedDepotBinding {
    fun merge(direct: Map<Int, String>, parents: Map<Int, Int>,
              inherited: Map<Int, String>): Map<Int, String> {
        require(direct.isNotEmpty() && direct.size <= 128)
        require(parents.size <= 128 && parents.keys.all { it > 0 } &&
            parents.values.all { it > 0 && it != 413150 })
        require(inherited.keys == parents.keys) { "Shared parent PICS response missing depot IDs" }
        require((direct.keys intersect inherited.keys).isEmpty()) { "Overlapping direct and shared depot" }
        val all = direct + inherited
        require(all.size <= 128 && all.keys.all { it > 0 } && all.values.all {
            it.matches(Regex("[0-9]{1,20}")) && it.any { c -> c != '0' }
        }) { "Invalid authenticated PICS manifest set" }
        return all
    }
}
