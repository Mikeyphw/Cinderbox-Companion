package com.sdvsync.mods.api

import com.sdvsync.mods.models.RemoteModFile
import java.net.URI
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Safe, read-only presentation of Nexus provider metadata; never grants downloads. */
object NexR2Display {
    private val executableBlocks = Regex("""(?is)<\s*(script|style|iframe|object|template|svg|form)\b[^>]*>.*?<\s*/\s*\1\s*>""")
    private val tags = Regex("""(?s)<[^>]{0,2048}>""")
    private val whitespace = Regex("""[ \t\u0000-\u001F]{2,}""")
    private val lineRuns = Regex("""\n{3,}""")
    private val numericEntity = Regex("""&#(x[0-9a-fA-F]{1,6}|[0-9]{1,7});""")
    private val htmlEntities = mapOf(
        "&amp;" to "&", "&quot;" to "\"", "&#39;" to "'",
        "&apos;" to "'", "&nbsp;" to " ", "&lt;" to "<", "&gt;" to ">"
    )

    fun text(raw: String?, maxLength: Int = 1600): String {
        if (raw.isNullOrBlank()) return ""
        // Bound input before regex processing; this is UI text, not a HTML renderer.
        var result = executableBlocks.replace(raw.take(24000), " ")
        result = tags.replace(result, " ")
        result = numericEntity.replace(result) { match ->
            val token = match.groupValues[1]
            val n = if (token.startsWith('x')) token.drop(1).toIntOrNull(16)
                    else token.toIntOrNull()
            if (n == null || n !in 32..0x10FFFF || n in 0xD800..0xDFFF) " "
            else String(Character.toChars(n))
        }
        htmlEntities.forEach { (entity, character) ->
            result = result.replace(entity, character, ignoreCase = true)
        }
        return lineRuns.replace(whitespace.replace(result, " "), "\n\n")
            .trim().take(maxLength.coerceIn(1, 6000)).trim()
    }

    /** Refuse non-Nexus schemes, embedded credentials, custom ports and lookalike hosts. */
    fun imageUrl(raw: String?): String? {
        if (raw.isNullOrBlank() || raw.length > 1200) return null
        return try {
            val url = URI(raw.trim())
            val host = url.host?.lowercase(Locale.ROOT) ?: return null
            if (!url.scheme.equals("https", ignoreCase = true) || url.userInfo != null ||
                url.port != -1 || url.fragment != null ||
                (host != "nexusmods.com" && !host.endsWith(".nexusmods.com"))) null
            else url.toASCIIString()
        } catch (_: IllegalArgumentException) { null }
    }

    fun dateUtc(value: Long): String? {
        if (value <= 0) return null
        return try {
            val instant = if (value >= 100_000_000_000L) Instant.ofEpochMilli(value)
                          else Instant.ofEpochSecond(value)
            if (instant.epochSecond !in 946684800L..4102444799L) null
            else DateTimeFormatter.ISO_LOCAL_DATE.withZone(ZoneOffset.UTC).format(instant)
        } catch (_: Exception) { null }
    }

    fun compactCount(value: Int): String = when {
        value < 0 -> "Unavailable"
        value >= 1_000_000 -> String.format(Locale.US, "%.1fM", value / 1_000_000.0)
        value >= 1_000 -> String.format(Locale.US, "%.1fK", value / 1_000.0)
        else -> value.toString()
    }

    fun fileSize(size: Long): String = when {
        size <= 0 -> "Size unavailable"
        size >= 1024L * 1024L -> String.format(Locale.US, "%.1f MiB", size / (1024.0 * 1024.0))
        size >= 1024L -> String.format(Locale.US, "%.1f KiB", size / 1024.0)
        else -> "$size B"
    }

    enum class FileGroup(val title: String) {
        MAIN("Main files"), UPDATES("Updates"), OPTIONAL("Optional files"),
        OLD("Old files"), OTHER("Other provider files")
    }

    data class Group(val kind: FileGroup, val files: List<RemoteModFile>)

    fun groupedFiles(input: List<RemoteModFile>): List<Group> {
        val bounded = input.asSequence()
            .filter { it.fileId.isNotBlank() && it.fileName.isNotBlank() }
            .distinctBy { it.fileId }
            .take(120).toList()
        val groups = bounded.groupBy { file ->
            when (file.categoryName.trim().lowercase(Locale.ROOT)) {
                "main", "main files", "main file" -> FileGroup.MAIN
                "update", "updates", "update files" -> FileGroup.UPDATES
                "optional", "optional files", "optional file" -> FileGroup.OPTIONAL
                "old", "old_version", "old files", "old version", "old versions" -> FileGroup.OLD
                else -> FileGroup.OTHER
            }
        }
        return FileGroup.entries.mapNotNull { section ->
            groups[section]?.takeIf { it.isNotEmpty() }?.let { Group(section, it) }
        }
    }
}
