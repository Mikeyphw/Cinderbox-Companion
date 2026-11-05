package com.sdvsync.mods

import com.sdvsync.mods.models.ModUpdateInfo
import java.util.Locale

/** Interpretation of an SMAPI candidate; unknown is not a clean up-to-date result. */
enum class UpdateAssessment { NEWER, CURRENT, INSTALLED_AHEAD, UNCOMPARABLE, UNKNOWN }

/** Pure metadata policy; never installs, downloads, or reads local mod files. */
object ModUpdatePolicy {
    private val format = Regex("^[0-9]+(?:\\.[0-9]+){0,3}(?:-[0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*)?(?:\\+[0-9A-Za-z.-]+)?$")
    private data class Parsed(val numbers: List<Int>, val prerelease: List<String>?)

    fun normalizedId(uniqueID: String): String {
        require(uniqueID.matches(Regex("[A-Za-z0-9_.-]{1,128}"))) { "Invalid SMAPI ID" }
        return uniqueID.lowercase(Locale.ROOT)
    }

    fun checkedCandidateVersion(version: String): String {
        require(version.length in 1..80 && version.isNotBlank() &&
            version.none { it.isISOControl() }) { "Invalid candidate version" }
        return version
    }

    private fun parse(raw: String): Parsed? {
        if (!format.matches(raw)) return null
        val withoutBuild = raw.substringBefore('+')
        val numberPart = withoutBuild.substringBefore('-')
        val parts = numberPart.split('.')
        if (parts.any { it.length > 1 && it[0] == '0' }) return null
        val numbers = parts.map { it.toIntOrNull() ?: return null }
        if (numbers.size > 4) return null
        val pre = withoutBuild.substringAfter('-', "").takeIf { it.isNotEmpty() }
            ?.split('.')
        if (pre?.any { it.isBlank() || (it.all(Char::isDigit) &&
                    it.length > 1 && it[0] == '0') } == true) return null
        return Parsed(numbers + List(4 - numbers.size) { 0 }, pre)
    }

    private fun comparePre(a: List<String>?, b: List<String>?): Int {
        if (a == null && b != null) return 1
        if (a != null && b == null) return -1
        if (a == null || b == null) return 0
        for (i in 0 until minOf(a.size, b.size)) {
            val x = a[i]; val y = b[i]
            val xn = x.toLongOrNull(); val yn = y.toLongOrNull()
            val diff = when {
                xn != null && yn != null -> xn.compareTo(yn)
                xn != null -> -1
                yn != null -> 1
                else -> x.compareTo(y)
            }
            if (diff != 0) return diff
        }
        return a.size.compareTo(b.size)
    }

    /** Only explicit numeric/pre-release patterns are considered orderable. */
    fun assess(installed: String, candidate: String?): UpdateAssessment {
        if (candidate.isNullOrBlank()) return UpdateAssessment.UNKNOWN
        if (installed == candidate) return UpdateAssessment.CURRENT
        val local = parse(installed) ?: return UpdateAssessment.UNCOMPARABLE
        val remote = parse(candidate) ?: return UpdateAssessment.UNCOMPARABLE
        for (i in 0..3) {
            val cmp = remote.numbers[i].compareTo(local.numbers[i])
            if (cmp > 0) return UpdateAssessment.NEWER
            if (cmp < 0) return UpdateAssessment.INSTALLED_AHEAD
        }
        val pre = comparePre(remote.prerelease, local.prerelease)
        return when {
            pre > 0 -> UpdateAssessment.NEWER
            pre < 0 -> UpdateAssessment.INSTALLED_AHEAD
            else -> UpdateAssessment.CURRENT
        }
    }

    /** Ignore only the exact candidate version of this specific normalized mod ID. */
    fun isIgnored(candidate: ModUpdateInfo, ignored: Map<String, String>): Boolean =
        ignored[normalizedId(candidate.uniqueID)] == candidate.latestVersion

    fun actionable(raw: Map<String, ModUpdateInfo>, ignored: Map<String, String>): Map<String, ModUpdateInfo> =
        raw.filterValues { item ->
            assess(item.installedVersion, item.latestVersion) == UpdateAssessment.NEWER &&
                !isIgnored(item, ignored)
        }

    fun ignored(raw: Map<String, ModUpdateInfo>, ignored: Map<String, String>): Map<String, ModUpdateInfo> =
        raw.filterValues { item ->
            assess(item.installedVersion, item.latestVersion) == UpdateAssessment.NEWER &&
                isIgnored(item, ignored)
        }
}
