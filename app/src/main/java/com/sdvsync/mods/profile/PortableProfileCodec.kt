package com.sdvsync.mods.profile

import com.sdvsync.mods.models.ModProfile
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.Locale
import java.util.UUID

/**
 * M25-01 profile metadata codec. Strict JSON allowlist: no file paths, API keys,
 * credentials, arbitrary serializable objects, mod content or config.json.
 */
object PortableProfileCodec {
    const val MAX_PORTABLE_BYTES = 262144
    const val MAX_MODS = 512
    const val MAX_PROFILES = 128
    private const val MAX_STORED_BYTES = 2097152
    private val modIdRegex = Regex("^[A-Za-z0-9_.-]{1,128}$")
    private val fields = setOf("id", "name", "enabledModIds", "createdAt", "modifiedAt",
        "description", "isProtected", "notes")

    fun checkedName(name: String): String = name.trim().also {
        require(it.length in 1..80 && it.none(Char::isISOControl)) { "Invalid profile name" }
    }

    fun canonicalId(id: String): String = id.lowercase(Locale.ROOT).also {
        require(modIdRegex.matches(id)) { "Invalid SMAPI UniqueID" }
    }

    private fun checkKeys(json: JSONObject, allow: Set<String>) {
        val iterator = json.keys()
        while (iterator.hasNext()) require(iterator.next() in allow) { "Unexpected field" }
    }

    private fun string(json: JSONObject, key: String, optional: Boolean = false): String {
        if (optional && !json.has(key)) return ""
        val raw = json.get(key)
        require(raw is String) { "Non-text profile field" }
        return raw
    }

    private fun readProfile(json: JSONObject, legacy: Boolean): ModProfile {
        checkKeys(json, if (legacy) setOf("name", "enabledModIds", "createdAt") else fields)
        val name = checkedName(string(json, "name"))
        val ids = json.getJSONArray("enabledModIds")
        require(ids.length() <= MAX_MODS) { "Too many mod identifiers" }
        val set = linkedSetOf<String>()
        repeat(ids.length()) { index ->
            val raw = ids.get(index)
            require(raw is String && set.add(canonicalId(raw))) { "Duplicate or invalid SMAPI UniqueID" }
        }
        val created = json.getLong("createdAt")
        require(created >= 0) { "Invalid creation time" }
        val uuid = if (legacy) {
            val stable = "cinderbox-m25-legacy:" + name.lowercase(Locale.ROOT) + ":" + created
            UUID.nameUUIDFromBytes(stable.toByteArray(Charsets.UTF_8)).toString()
        } else string(json, "id")
        require(runCatching { UUID.fromString(uuid).toString() == uuid.lowercase(Locale.ROOT) }
            .getOrDefault(false)) { "Invalid profile UUID" }
        val changed = if (legacy) created else json.getLong("modifiedAt")
        require(changed >= 0) { "Invalid modification time" }
        val description = if (legacy) "" else string(json, "description", optional = true)
        require(description.length <= 500 && '\u0000' !in description) { "Invalid description" }
        val isProtected = if (!legacy && json.has("isProtected")) json.getBoolean("isProtected") else false
        val notes = linkedMapOf<String, String>()
        if (!legacy && json.has("notes")) {
            val source = json.getJSONObject("notes")
            require(source.length() <= 256) { "Too many notes" }
            val keys = source.keys()
            while (keys.hasNext()) {
                val rawId = keys.next()
                val rawNote = source.get(rawId)
                require(rawNote is String && rawNote.length <= 1200 && '\u0000' !in rawNote) {
                    "Invalid note"
                }
                require(notes.put(canonicalId(rawId), rawNote) == null) { "Duplicate note" }
            }
        }
        return ModProfile(name, set, created, uuid, changed, description, isProtected, notes)
    }

    private fun writeProfile(profile: ModProfile): JSONObject {
        val normalized = readProfile(JSONObject().apply {
            put("name", profile.name)
            put("id", profile.id)
            put("enabledModIds", JSONArray(profile.enabledModIds.sorted()))
            put("createdAt", profile.createdAt)
            put("modifiedAt", profile.modifiedAt)
            put("description", profile.description)
            put("isProtected", profile.isProtected)
            put("notes", JSONObject().apply {
                profile.notes.toSortedMap().forEach { (key, value) -> put(key, value) }
            })
        }, legacy = false)
        return JSONObject().apply {
            put("name", normalized.name)
            put("id", normalized.id)
            put("enabledModIds", JSONArray(normalized.enabledModIds.sorted()))
            put("createdAt", normalized.createdAt)
            put("modifiedAt", normalized.modifiedAt)
            put("description", normalized.description)
            put("isProtected", normalized.isProtected)
            put("notes", JSONObject().apply {
                normalized.notes.toSortedMap().forEach { (key, value) -> put(key, value) }
            })
        }
    }

    private fun checkUnique(profiles: List<ModProfile>) {
        require(profiles.size <= MAX_PROFILES) { "Too many profiles" }
        require(profiles.map { it.id }.distinct().size == profiles.size) { "Duplicate profile identity" }
        require(profiles.map { it.name.lowercase(Locale.ROOT) }.distinct().size == profiles.size) {
            "Duplicate profile name"
        }
    }

    /** Deterministically read legacy profile arrays without writing/mutating their original bytes. */
    fun decodeStored(text: String): List<ModProfile> {
        require(text.toByteArray(Charsets.UTF_8).size <= MAX_STORED_BYTES) { "Stored profiles too large" }
        val legacy = text.trimStart().startsWith("[")
        val array = if (legacy) JSONArray(text) else JSONObject(text).let { root ->
            checkKeys(root, setOf("schema_version", "profiles"))
            require(root.getInt("schema_version") == 2) { "Unknown stored profile schema" }
            root.getJSONArray("profiles")
        }
        require(array.length() <= MAX_PROFILES) { "Too many profiles" }
        val profiles = (0 until array.length()).map { readProfile(array.getJSONObject(it), legacy) }
        checkUnique(profiles)
        return profiles
    }

    fun encodeStored(profiles: List<ModProfile>): String {
        checkUnique(profiles)
        val text = JSONObject().apply {
            put("schema_version", 2)
            put("profiles", JSONArray().also { array ->
                profiles.forEach { array.put(writeProfile(it)) }
            })
        }.toString()
        require(text.toByteArray(Charsets.UTF_8).size <= MAX_STORED_BYTES) { "Stored profiles too large" }
        return text
    }

    fun export(profile: ModProfile): ByteArray {
        val bytes = JSONObject().apply {
            put("format", "cinderbox-mod-profile")
            put("schema_version", 1)
            put("profile", writeProfile(profile))
        }.toString(2).toByteArray(Charsets.UTF_8)
        require(bytes.size <= MAX_PORTABLE_BYTES) { "Profile export too large" }
        return bytes
    }

    fun import(input: InputStream): ModProfile {
        val out = ByteArrayOutputStream()
        val chunk = ByteArray(8192)
        input.use { stream ->
            while (true) {
                val n = stream.read(chunk)
                if (n < 0) break
                require(out.size() + n <= MAX_PORTABLE_BYTES) { "Profile import too large" }
                out.write(chunk, 0, n)
            }
        }
        val text = Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(out.toByteArray())).toString()
        val root = JSONObject(text)
        checkKeys(root, setOf("format", "schema_version", "profile"))
        require(root.getString("format") == "cinderbox-mod-profile") { "Unrecognized profile format" }
        require(root.getInt("schema_version") == 1) { "Unsupported profile schema" }
        return readProfile(root.getJSONObject("profile"), legacy = false)
    }
}
