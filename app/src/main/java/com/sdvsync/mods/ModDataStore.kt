package com.sdvsync.mods

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.models.AssociatedMod
import com.sdvsync.mods.models.ModProfile
import com.sdvsync.mods.profile.PortableProfileCodec
import com.sdvsync.mods.models.ModUpdateInfo
import com.sdvsync.mods.ModUpdatePolicy
import com.sdvsync.mods.models.SaveModAssociation
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import org.json.JSONArray
import org.json.JSONObject

private val Context.modDataStore by preferencesDataStore(name = "mod_data")

/**
 * Persistent storage for mod-related data.
 * API key stored in EncryptedSharedPreferences, other data in DataStore.
 */
class ModDataStore(private val context: Context) {

    companion object {
        private const val TAG = "ModDataStore"
        private val UPDATE_CACHE_KEY = stringPreferencesKey("update_cache")
        private val LAST_UPDATE_CHECK_KEY = longPreferencesKey("last_update_check")
        private val UPDATE_OBSERVATION_KEY = stringPreferencesKey("m25_update_observations_v1")
        private val IGNORED_UPDATE_VERSIONS_KEY = stringPreferencesKey("ignored_update_versions")
        private val MOD_METADATA_KEY = stringPreferencesKey("mod_metadata")
        private val PROFILES_KEY = stringPreferencesKey("mod_profiles")
        private val SAVE_MOD_ASSOCIATIONS_KEY = stringPreferencesKey("save_mod_associations")

        private const val ENCRYPTED_PREFS_NAME = "mod_encrypted_prefs"
        private const val KEY_NEXUS_API_KEY = "nexus_api_key"
    }

    private val encryptedPrefs by lazy {
        try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                ENCRYPTED_PREFS_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            AppLogger.e(TAG, "Failed to create EncryptedSharedPreferences", e)
            null
        }
    }

    // ── API Key ─────────────────────────────────────────────────────────

    fun getNexusApiKey(): String? = encryptedPrefs?.getString(KEY_NEXUS_API_KEY, null)

    fun setNexusApiKey(key: String?) {
        encryptedPrefs?.edit()?.apply {
            if (key != null) {
                putString(KEY_NEXUS_API_KEY, key)
            } else {
                remove(KEY_NEXUS_API_KEY)
            }
            apply()
        }
    }

    // ── Update Cache ────────────────────────────────────────────────────

    suspend fun getUpdateCache(): Map<String, ModUpdateInfo> = context.modDataStore.data
        .map { prefs ->
            prefs[UPDATE_CACHE_KEY]?.let { parseUpdateCache(it) } ?: emptyMap()
        }
        .first()

    suspend fun setUpdateCache(updates: Map<String, ModUpdateInfo>) {
        context.modDataStore.edit { prefs ->
            prefs[UPDATE_CACHE_KEY] = serializeUpdateCache(updates)
            prefs[LAST_UPDATE_CHECK_KEY] = System.currentTimeMillis()
        }
    }

    /** Fails closed on invalid stored observations; a failure never erases cached state. */
    suspend fun getUpdateObservations(): Map<String, ModUpdateObservation> =
        context.modDataStore.data.map { prefs ->
            prefs[UPDATE_OBSERVATION_KEY]?.let { ModUpdateObservationCodec.decode(it) }
                ?: emptyMap()
        }.first()

    /** Cache, observations and successful timestamp advance in one DataStore edit. */
    suspend fun setUpdateSnapshot(snapshot: ModUpdateCheckResult) {
        require(snapshot.checkedAtMs > 0L) { "Invalid update check timestamp" }
        val encoded = ModUpdateObservationCodec.encode(snapshot.observations)
        val cache = serializeUpdateCache(snapshot.updates)
        context.modDataStore.edit { prefs ->
            prefs[UPDATE_CACHE_KEY] = cache
            prefs[UPDATE_OBSERVATION_KEY] = encoded
            prefs[LAST_UPDATE_CHECK_KEY] = snapshot.checkedAtMs
        }
    }

    suspend fun getLastUpdateCheck(): Long = context.modDataStore.data
        .map { prefs -> prefs[LAST_UPDATE_CHECK_KEY] ?: 0L }
        .first()

    /** Atomic version-specific ignore preference. Never changes installed files. */
    suspend fun ignoredUpdateVersions(): Map<String, String> = context.modDataStore.data
        .map { prefs -> parseIgnoredUpdates(prefs[IGNORED_UPDATE_VERSIONS_KEY]) }
        .first()

    suspend fun setIgnoredUpdateVersion(uniqueID: String, version: String?) {
        val key = ModUpdatePolicy.normalizedId(uniqueID)
        require(key.length <= 128 && key.isNotBlank())
        if (version != null) ModUpdatePolicy.checkedCandidateVersion(version)
        context.modDataStore.edit { prefs ->
            val existing = parseIgnoredUpdates(prefs[IGNORED_UPDATE_VERSIONS_KEY]).toMutableMap()
            if (version == null) existing.remove(key) else existing[key] = version
            require(existing.size <= 512) { "Too many ignored update preferences" }
            val json = JSONObject()
            existing.toSortedMap().forEach { (id, candidate) -> json.put(id, candidate) }
            prefs[IGNORED_UPDATE_VERSIONS_KEY] = json.toString()
        }
    }

    /** Invalid ignore metadata must not be silently replaced with an empty list. */
    private fun parseIgnoredUpdates(raw: String?): Map<String, String> {
        if (raw == null) return emptyMap()
        require(raw.length <= 65536) { "Ignored update metadata is too large" }
        val objectValue = JSONObject(raw)
        require(objectValue.length() <= 512) { "Too many ignored updates" }
        val output = linkedMapOf<String, String>()
        val keys = objectValue.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val value = objectValue.get(key)
            require(value is String) { "Invalid candidate version type" }
            val id = ModUpdatePolicy.normalizedId(key)
            ModUpdatePolicy.checkedCandidateVersion(value)
            require(output.put(id, value) == null) { "Duplicate ignored update ID" }
        }
        return output
    }

    // ── Mod Metadata (install source, timestamps) ───────────────────────

    suspend fun getModMetadata(uniqueId: String): ModMetadata? {
        val all = getAllModMetadata()
        return all[uniqueId]
    }

    suspend fun setModMetadata(uniqueId: String, metadata: ModMetadata) {
        val all = getAllModMetadata().toMutableMap()
        all[uniqueId] = metadata
        context.modDataStore.edit { prefs ->
            prefs[MOD_METADATA_KEY] = serializeMetadata(all)
        }
    }

    suspend fun removeModMetadata(uniqueId: String) {
        val all = getAllModMetadata().toMutableMap()
        all.remove(uniqueId)
        context.modDataStore.edit { prefs ->
            prefs[MOD_METADATA_KEY] = serializeMetadata(all)
        }
    }

    suspend fun getAllModMetadata(): Map<String, ModMetadata> = context.modDataStore.data
        .map { prefs ->
            prefs[MOD_METADATA_KEY]?.let { parseMetadata(it) } ?: emptyMap()
        }
        .first()

    // ── M25-01 versioned, fail-closed mod profiles ──────────────────
    suspend fun getProfiles(): List<ModProfile> = context.modDataStore.data
        .map { prefs ->
            prefs[PROFILES_KEY]?.let { PortableProfileCodec.decodeStored(it) } ?: emptyList()
        }.first()

    /** Entire read/modify/write is one DataStore edit. Invalid old data is never erased. */
    suspend fun saveProfile(profile: ModProfile) {
        context.modDataStore.edit { prefs ->
            val profiles = prefs[PROFILES_KEY]?.let {
                PortableProfileCodec.decodeStored(it)
            }?.toMutableList() ?: mutableListOf()
            val name = PortableProfileCodec.checkedName(profile.name)
            require(profiles.none { it.id != profile.id && it.name.equals(name, ignoreCase = true) }) {
                "Another profile already has this name"
            }
            val index = profiles.indexOfFirst { it.id == profile.id }
            if (index >= 0) {
                require(!profiles[index].isProtected || profiles[index] == profile) {
                    "Protected profile cannot be edited"
                }
                profiles[index] = profile.copy(name = name)
            } else {
                profiles.add(profile.copy(name = name))
            }
            prefs[PROFILES_KEY] = PortableProfileCodec.encodeStored(profiles)
        }
    }

    suspend fun deleteProfile(name: String) {
        context.modDataStore.edit { prefs ->
            val profiles = prefs[PROFILES_KEY]?.let {
                PortableProfileCodec.decodeStored(it)
            } ?: emptyList()
            val selected = profiles.firstOrNull { it.name.equals(name, ignoreCase = true) }
                ?: return@edit
            require(!selected.isProtected) { "Protected profile cannot be deleted" }
            prefs[PROFILES_KEY] = PortableProfileCodec.encodeStored(
                profiles.filter { it.id != selected.id }
            )
        }
    }

    // ── Save Mod Associations ──────────────────────────────────────────

    suspend fun getSaveModAssociation(saveFolderName: String): SaveModAssociation? = context.modDataStore.data
        .map { prefs ->
            prefs[SAVE_MOD_ASSOCIATIONS_KEY]?.let { parseAssociations(it) }?.get(saveFolderName)
        }
        .first()

    suspend fun setSaveModAssociation(association: SaveModAssociation) {
        val all = getAllAssociations().toMutableMap()
        all[association.saveFolderName] = association
        context.modDataStore.edit { prefs ->
            prefs[SAVE_MOD_ASSOCIATIONS_KEY] = serializeAssociations(all)
        }
    }

    suspend fun deleteSaveModAssociation(saveFolderName: String) {
        val all = getAllAssociations().toMutableMap()
        all.remove(saveFolderName)
        context.modDataStore.edit { prefs ->
            prefs[SAVE_MOD_ASSOCIATIONS_KEY] = serializeAssociations(all)
        }
    }

    private suspend fun getAllAssociations(): Map<String, SaveModAssociation> = context.modDataStore.data
        .map { prefs ->
            prefs[SAVE_MOD_ASSOCIATIONS_KEY]?.let { parseAssociations(it) } ?: emptyMap()
        }
        .first()

    private fun serializeAssociations(associations: Map<String, SaveModAssociation>): String {
        val obj = JSONObject()
        associations.forEach { (saveName, assoc) ->
            val modsArray = JSONArray()
            assoc.enabledMods.forEach { mod ->
                modsArray.put(
                    JSONObject().apply {
                        put("uniqueID", mod.uniqueID)
                        put("name", mod.name)
                        put("version", mod.version)
                    }
                )
            }
            obj.put(
                saveName,
                JSONObject().apply {
                    put("capturedAt", assoc.capturedAt)
                    put("mods", modsArray)
                }
            )
        }
        return obj.toString()
    }

    private fun parseAssociations(json: String): Map<String, SaveModAssociation> = try {
        val obj = JSONObject(json)
        val result = mutableMapOf<String, SaveModAssociation>()
        obj.keys().forEach { saveName ->
            val item = obj.getJSONObject(saveName)
            val modsArray = item.getJSONArray("mods")
            val mods = (0 until modsArray.length()).map { i ->
                val modObj = modsArray.getJSONObject(i)
                AssociatedMod(
                    uniqueID = modObj.getString("uniqueID"),
                    name = modObj.getString("name"),
                    version = modObj.getString("version")
                )
            }.toSet()
            result[saveName] = SaveModAssociation(
                saveFolderName = saveName,
                enabledMods = mods,
                capturedAt = item.optLong("capturedAt", 0)
            )
        }
        result
    } catch (e: Exception) {
        AppLogger.e(TAG, "Failed to parse save mod associations", e)
        emptyMap()
    }

    // ── Serialization ───────────────────────────────────────────────────

    private fun serializeUpdateCache(updates: Map<String, ModUpdateInfo>): String {
        val obj = JSONObject()
        updates.forEach { (id, info) ->
            obj.put(
                id,
                JSONObject().apply {
                    put("uniqueID", info.uniqueID)
                    put("installedVersion", info.installedVersion)
                    put("latestVersion", info.latestVersion)
                    put("updateUrl", info.updateUrl ?: JSONObject.NULL)
                    put("source", info.source)
                    put("changelogHtml", info.changelogHtml ?: JSONObject.NULL)
                }
            )
        }
        return obj.toString()
    }

    private fun parseUpdateCache(json: String): Map<String, ModUpdateInfo> = try {
        val obj = JSONObject(json)
        val result = mutableMapOf<String, ModUpdateInfo>()
        obj.keys().forEach { key ->
            val item = obj.getJSONObject(key)
            result[key] = ModUpdateInfo(
                uniqueID = item.getString("uniqueID"),
                installedVersion = item.getString("installedVersion"),
                latestVersion = item.getString("latestVersion"),
                updateUrl = item.optString("updateUrl").takeIf { it != "null" && it.isNotBlank() },
                source = item.getString("source"),
                changelogHtml = item.optString("changelogHtml").takeIf { it != "null" && it.isNotBlank() }
            )
        }
        result
    } catch (e: Exception) {
        AppLogger.e(TAG, "Failed to parse update cache", e)
        emptyMap()
    }

    private fun serializeMetadata(metadata: Map<String, ModMetadata>): String {
        val obj = JSONObject()
        metadata.forEach { (id, meta) ->
            obj.put(
                id,
                JSONObject().apply {
                    put("installedFrom", meta.installedFrom ?: JSONObject.NULL)
                    put("installedAt", meta.installedAt)
                }
            )
        }
        return obj.toString()
    }

    private fun parseMetadata(json: String): Map<String, ModMetadata> = try {
        val obj = JSONObject(json)
        val result = mutableMapOf<String, ModMetadata>()
        obj.keys().forEach { key ->
            val item = obj.getJSONObject(key)
            result[key] = ModMetadata(
                installedFrom = item.optString("installedFrom").takeIf { it != "null" && it.isNotBlank() },
                installedAt = item.optLong("installedAt", 0)
            )
        }
        result
    } catch (e: Exception) {
        AppLogger.e(TAG, "Failed to parse mod metadata", e)
        emptyMap()
    }
}

data class ModMetadata(val installedFrom: String? = null, val installedAt: Long = 0)
