package com.sdvsync.mods.profile

import com.sdvsync.mods.models.ModProfile
import java.io.ByteArrayInputStream
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import androidx.test.ext.junit.runners.AndroidJUnit4

/** Disposable Android fixtures; no Steam, mods root, private user data or file mutations. */
@RunWith(AndroidJUnit4::class)
class M25PortableProfileDeviceTest {
    @Test fun metadataRoundtripAndNoPaths() {
        val item = ModProfile("Test farm", setOf("Author.Example"),
            notes = mapOf("Author.Example" to "Personal notes"))
        val portable = PortableProfileCodec.export(item)
        val text = String(portable, Charsets.UTF_8)
        assertFalse(text.contains("/storage/emulated"))
        assertFalse(text.contains("nexus_api_key"))
        val decoded = PortableProfileCodec.import(ByteArrayInputStream(portable))
        assertEquals(item.id, decoded.id)
        assertEquals(setOf("author.example"), decoded.enabledModIds)
        assertEquals("Personal notes", decoded.notes["author.example"])
    }

    @Test fun legacyMigrationIsStableAcrossLoadsAndStoreWrites() {
        val old = """[{"name":"Farm","enabledModIds":["My.Mod"],"createdAt":2}]"""
        val profile = PortableProfileCodec.decodeStored(old).single()
        assertEquals(profile.id, PortableProfileCodec.decodeStored(old).single().id)
        assertEquals(profile.id, PortableProfileCodec.decodeStored(
            PortableProfileCodec.encodeStored(listOf(profile))).single().id)
    }

    @Test fun rejectsDuplicateIdsAndUnexpectedSchema() {
        val json = JSONObject(String(PortableProfileCodec.export(
            ModProfile("Farm", setOf("A.Mod"))), Charsets.UTF_8))
        json.getJSONObject("profile").put("enabledModIds",
            JSONArray().put("A.Mod").put("a.mod"))
        assertTrue(runCatching { PortableProfileCodec.import(
            ByteArrayInputStream(json.toString().toByteArray(Charsets.UTF_8))) }.isFailure)
        val altered = JSONObject(String(PortableProfileCodec.export(
            ModProfile("Farm", setOf("A.Mod"))), Charsets.UTF_8))
        altered.put("schema_version", 4)
        assertTrue(runCatching { PortableProfileCodec.import(
            ByteArrayInputStream(altered.toString().toByteArray(Charsets.UTF_8))) }.isFailure)
    }

    @Test fun rejectsInvalidUtf8OversizeAndCorruptLegacyWithoutMutatingBytes() {
        assertTrue(runCatching { PortableProfileCodec.import(
            ByteArrayInputStream(byteArrayOf(0xc3.toByte(), 0x28))) }.isFailure)
        assertTrue(runCatching { PortableProfileCodec.import(ByteArrayInputStream(
            ByteArray(PortableProfileCodec.MAX_PORTABLE_BYTES + 1) { 0x20.toByte() })) }.isFailure)
        val corrupt = "[{broken json"
        assertTrue(runCatching { PortableProfileCodec.decodeStored(corrupt) }.isFailure)
        assertEquals("[{broken json", corrupt)
    }
}
