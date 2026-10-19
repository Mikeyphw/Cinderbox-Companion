import com.sdvsync.download.M24SharedDepotBinding

fun main() {
    val parent = mapOf(229002 to 228980, 229012 to 228980)
    val direct = mapOf(413151 to "123")
    val got = M24SharedDepotBinding.merge(direct, parent, mapOf(229002 to "234", 229012 to "345"))
    check(got.size == 3)
    check(runCatching { M24SharedDepotBinding.merge(direct, parent, emptyMap()) }.isFailure)
    check(runCatching { M24SharedDepotBinding.merge(direct, parent, mapOf(229002 to "3", 229012 to "0")) }.isFailure)
    check(runCatching { M24SharedDepotBinding.merge(direct, mapOf(413151 to 228980), mapOf(413151 to "3")) }.isFailure)
    check(M24SharedDepotBinding.merge(direct, emptyMap(), emptyMap()) == direct)
    println("PASS_M24_SHARED_DEPOT_BINDING_NEGATIVE_CONTROLS")
}
