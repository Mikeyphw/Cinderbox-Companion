package com.sdvsync.ui.viewmodels

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sdvsync.cinderbox.CinderboxLayoutEvents
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.ModDataStore
import com.sdvsync.mods.ModUpdatePolicy
import com.sdvsync.mods.ModFileManager
import com.sdvsync.mods.ModCompatibility
import com.sdvsync.mods.ModCompatibilityIssue
import com.sdvsync.mods.ModProfilePreview
import com.sdvsync.mods.ModArchivePreview
import com.sdvsync.mods.ModReviewQueue
import com.sdvsync.mods.ModSnapshot
import com.sdvsync.mods.api.SmapiUpdateChecker
import com.sdvsync.mods.models.InstallResult
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModProfile
import com.sdvsync.mods.profile.PortableProfileCodec
import java.util.UUID
import com.sdvsync.mods.models.ModUpdateInfo
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class ModSortOrder { NAME, AUTHOR, STATUS }
enum class ModFilter { ALL, ENABLED, DISABLED, HAS_UPDATE }

data class ModManagerState(
    val installedMods: List<InstalledMod> = emptyList(),
    val updates: Map<String, ModUpdateInfo> = emptyMap(),
    val rawUpdates: Map<String, ModUpdateInfo> = emptyMap(),
    val ignoredUpdates: Map<String, ModUpdateInfo> = emptyMap(),
    val showIgnoredUpdates: Boolean = false,
    val updateError: String? = null,
    val isLoading: Boolean = true,
    val isCheckingUpdates: Boolean = false,
    val error: String? = null,
    val importMessage: String? = null,
    val pendingPreview: ModArchivePreview? = null,
    val pendingLabel: String = "",
    val hasPendingReview: Boolean = false,
    val isApplyingReview: Boolean = false,
    val snapshots: List<ModSnapshot> = emptyList(),
    val sortOrder: ModSortOrder = ModSortOrder.NAME,
    val filter: ModFilter = ModFilter.ALL,
    val searchQuery: String = "",
    val displayedMods: List<InstalledMod> = emptyList(),
    val profiles: List<ModProfile> = emptyList(),
    val activeProfileName: String? = null,
    val isApplyingProfile: Boolean = false,
    val compatibilityIssues: List<ModCompatibilityIssue> = emptyList(),
    val profileMessage: String? = null,
    val pendingPortableProfile: PortableProfileReview? = null
)

/** The import candidate is metadata only and never implies any mod action. */
data class PortableProfileReview(
    val profile: ModProfile,
    val missingMods: List<String>,
    val blockers: List<String>,
    val proposedChanges: Int,
    val inventoryFingerprint: String,
    val nameTaken: Boolean
)

class ModManagerViewModel(
    private val context: Context,
    private val fileManager: ModFileManager,
    private val dataStore: ModDataStore,
    private val updateChecker: SmapiUpdateChecker
) : ViewModel() {

    companion object {
        private const val TAG = "ModManagerVM"
        private const val UPDATE_CHECK_INTERVAL_MS = 4 * 60 * 60 * 1000L // 4 hours
    }

    private val pending = ModReviewQueue(context.filesDir)
    private val _state = MutableStateFlow(ModManagerState())
    val state: StateFlow<ModManagerState> = _state.asStateFlow()

    init {
        loadInstalledMods()
        refreshSafetyState()
        viewModelScope.launch {
            CinderboxLayoutEvents.changed.collect { loadInstalledMods() }
        }
    }

    fun loadInstalledMods() {
        viewModelScope.launch(Dispatchers.IO) {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val mods = fileManager.listInstalledMods()
                val rawUpdates = dataStore.getUpdateCache()
                val ignored = dataStore.ignoredUpdateVersions()
                val actionable = ModUpdatePolicy.actionable(rawUpdates, ignored)
                _state.update {
                    it.copy(installedMods = mods, updates = actionable,
                        rawUpdates = rawUpdates,
                        ignoredUpdates = ModUpdatePolicy.ignored(rawUpdates, ignored),
                        isLoading = false, compatibilityIssues = ModCompatibility.audit(mods))
                }
                updateDisplayedMods()
                loadProfiles()
                refreshSafetyState()

                // Auto-check for updates if stale
                val lastCheck = dataStore.getLastUpdateCheck()
                val now = System.currentTimeMillis()
                if (mods.isNotEmpty() && (lastCheck <= 0L || lastCheck > now ||
                        now - lastCheck > UPDATE_CHECK_INTERVAL_MS)) {
                    checkForUpdates()
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to load mods", e)
                _state.update {
                    it.copy(isLoading = false, error = e.message ?: "Failed to load mods")
                }
            }
        }
    }

    fun checkForUpdates() {
        val mods = _state.value.installedMods
        if (mods.isEmpty()) return

        viewModelScope.launch(Dispatchers.IO) {
            _state.update { it.copy(isCheckingUpdates = true) }
            try {
                // Only check enabled mods
                val enabledMods = mods.filter { it.enabled }
                val updates = updateChecker.checkForUpdates(enabledMods)

                // A successful check is the only path permitted to replace cache.
                dataStore.setUpdateCache(updates)
                val ignored = dataStore.ignoredUpdateVersions()
                _state.update { it.copy(
                    rawUpdates = updates,
                    updates = ModUpdatePolicy.actionable(updates, ignored),
                    ignoredUpdates = ModUpdatePolicy.ignored(updates, ignored),
                    updateError = null, isCheckingUpdates = false) }
                updateDisplayedMods()
            } catch (e: Exception) {
                AppLogger.w(TAG, "Update check unavailable; previous cache retained")
                _state.update { it.copy(isCheckingUpdates = false,
                    updateError = "Update status unavailable; previous results retained") }
            }
        }
    }

    fun toggleIgnoredUpdates() {
        _state.update { it.copy(showIgnoredUpdates = !it.showIgnoredUpdates) }
    }

    fun ignoreUpdate(uniqueID: String) = changeIgnoredVersion(uniqueID, ignore = true)
    fun unignoreUpdate(uniqueID: String) = changeIgnoredVersion(uniqueID, ignore = false)

    private fun changeIgnoredVersion(uniqueID: String, ignore: Boolean) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val id = ModUpdatePolicy.normalizedId(uniqueID)
                val raw = _state.value.rawUpdates.values.firstOrNull {
                    ModUpdatePolicy.normalizedId(it.uniqueID) == id
                } ?: return@launch
                dataStore.setIgnoredUpdateVersion(id, if (ignore) raw.latestVersion else null)
                val ignored = dataStore.ignoredUpdateVersions()
                _state.update { it.copy(
                    updates = ModUpdatePolicy.actionable(it.rawUpdates, ignored),
                    ignoredUpdates = ModUpdatePolicy.ignored(it.rawUpdates, ignored)) }
                updateDisplayedMods()
            } catch (e: Exception) {
                _state.update { it.copy(updateError = "Update preference not changed") }
            }
        }
    }

    fun toggleMod(folderName: String, enable: Boolean) {
        viewModelScope.launch(Dispatchers.IO) {
            val success = if (enable) {
                fileManager.enableMod(folderName)
            } else {
                fileManager.disableMod(folderName)
            }
            if (success) {
                loadInstalledMods()
            }
        }
    }

    fun removeMod(folderName: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val mod = _state.value.installedMods.find { it.folderName == folderName }
            if (fileManager.removeMod(folderName)) {
                mod?.let { dataStore.removeModMetadata(it.manifest.uniqueID) }
                loadInstalledMods()
            }
        }
    }

    fun refreshSafetyState() {
        viewModelScope.launch(Dispatchers.IO) {
            val zip = pending.archive()
            val review = zip?.let { runCatching { fileManager.previewFromZip(it) }.getOrNull() }
            _state.update { it.copy(hasPendingReview = pending.hasPending(),
                pendingPreview = review, pendingLabel = pending.description(),
                snapshots = fileManager.listRetainedSnapshots()) }
        }
    }

    fun importFromUri(uri: Uri) {
        viewModelScope.launch(Dispatchers.IO) {
            val temp = File(context.cacheDir, "m5-import-${System.currentTimeMillis()}.zip")
            try {
                check(!pending.hasPending()) { "A mod is already awaiting review" }
                val input = context.contentResolver.openInputStream(uri)
                    ?: error("Cannot read archive")
                input.use { source -> temp.outputStream().use { target -> source.copyTo(target) } }
                pending.enqueue(temp, "Imported mod archive", "local", "")
                _state.update { it.copy(importMessage = "Review the proposed changes before installing") }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Mod import staging failed", e)
                _state.update { it.copy(importMessage = "Import failed: ${e.message}") }
            } finally {
                temp.delete()
                refreshSafetyState()
            }
        }
    }

    fun confirmPendingReview() {
        viewModelScope.launch(Dispatchers.IO) {
            _state.update { it.copy(isApplyingReview = true) }
            try {
                val archive = requireNotNull(pending.archive()) { "No pending mod" }
                val prior = requireNotNull(_state.value.pendingPreview) { "Cannot approve an invalid archive" }
                val result = fileManager.installFromZip(archive, prior.approvalKey)
                when (result) {
                    is InstallResult.Success -> {
                        val (source, modId) = pending.source()
                        if (source != "local") {
                            result.mods.forEach { mod -> dataStore.setModMetadata(mod.manifest.uniqueID,
                                com.sdvsync.mods.ModMetadata(installedFrom = "$source:$modId",
                                    installedAt = System.currentTimeMillis())) }
                        }
                        pending.clear()
                        _state.update { it.copy(importMessage = "Installed: ${result.mods.joinToString { m -> m.manifest.name }}") }
                        loadInstalledMods()
                    }
                    is InstallResult.Error -> _state.update {
                        it.copy(importMessage = "Installation rejected: ${result.message}") }
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Reviewed mod installation failed", e)
                _state.update { it.copy(importMessage = "Installation failed: ${e.message}") }
            } finally {
                _state.update { it.copy(isApplyingReview = false) }
                refreshSafetyState()
            }
        }
    }

    fun discardPendingReview() {
        viewModelScope.launch(Dispatchers.IO) {
            runCatching { pending.clear() }.onFailure {
                _state.update { old -> old.copy(importMessage = "Cannot discard: ${it.message}") }
            }
            refreshSafetyState()
        }
    }

    fun restoreRetainedSnapshot(id: String) {
        viewModelScope.launch(Dispatchers.IO) {
            runCatching { fileManager.restoreSnapshot(id) }.onSuccess { restored ->
                _state.update { it.copy(importMessage = if (restored) "Mod restored from snapshot" else "Snapshot not found") }
                loadInstalledMods()
            }.onFailure { error ->
                _state.update { it.copy(importMessage = "Restore failed: ${error.message}") }
            }
            refreshSafetyState()
        }
    }

    fun clearImportMessage() {
        _state.update { it.copy(importMessage = null) }
    }

    fun setFilter(filter: ModFilter) {
        _state.update { it.copy(filter = filter) }
        updateDisplayedMods()
    }

    fun setSortOrder(order: ModSortOrder) {
        _state.update { it.copy(sortOrder = order) }
        updateDisplayedMods()
    }

    fun setSearchQuery(query: String) {
        _state.update { it.copy(searchQuery = query) }
        updateDisplayedMods()
    }

    // ── Profiles ─────────────────────────────────────────────────────────

    private fun loadProfiles() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val profiles = dataStore.getProfiles()
                _state.update {
                    it.copy(profiles = profiles, activeProfileName = detectActiveProfile(profiles))
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "M25 profile decode refused", e)
                _state.update { it.copy(profileMessage = "Profiles unreadable; original stored data was kept") }
            }
        }
    }

    fun saveCurrentAsProfile(name: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val ids = _state.value.installedMods.filter { it.enabled }
                    .map { it.manifest.uniqueID }.toSet()
                val label = PortableProfileCodec.checkedName(name)
                val prior = dataStore.getProfiles().firstOrNull {
                    it.name.equals(label, ignoreCase = true)
                }
                // Keep the existing UUID, notes and other metadata when resaving
                // the current loadout under an existing name (the pre-M25 behavior).
                // A protected profile is never silently replaced.
                require(prior?.isProtected != true) { "Protected profile" }
                val profile = prior?.copy(enabledModIds = ids,
                    modifiedAt = System.currentTimeMillis()) ?: ModProfile(label, ids)
                dataStore.saveProfile(profile)
                _state.update { it.copy(profileMessage = "Profile saved") }
                loadProfiles()
            } catch (e: Exception) {
                _state.update { it.copy(profileMessage = "Profile not saved; check name or stored data") }
            }
        }
    }

    fun exportPortableProfile(profile: ModProfile, uri: Uri) {
        viewModelScope.launch(Dispatchers.IO) {
            val successful = runCatching {
                val item = dataStore.getProfiles().single { it.id == profile.id }
                val payload = PortableProfileCodec.export(item)
                val output = requireNotNull(context.contentResolver.openOutputStream(uri, "w"))
                output.use { it.write(payload) }
            }.isSuccess
            _state.update { it.copy(profileMessage = if (successful)
                "Profile exported (metadata only)" else "Profile export failed") }
        }
    }

    fun previewPortableImport(uri: Uri) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val input = requireNotNull(context.contentResolver.openInputStream(uri))
                val imported = PortableProfileCodec.import(input)
                val installed = _state.value.installedMods
                val installedIds = installed.map {
                    PortableProfileCodec.canonicalId(it.manifest.uniqueID)
                }.toSet()
                val missing = imported.enabledModIds.filter { it !in installedIds }.sorted()
                val preview = ModCompatibility.preview(installed, imported)
                val existing = dataStore.getProfiles().any {
                    it.name.equals(imported.name, ignoreCase = true)
                }
                _state.update { it.copy(
                    pendingPortableProfile = PortableProfileReview(
                        imported, missing, preview.blockers.map { issue -> issue.message }.take(12),
                        preview.steps.size, preview.fingerprint, existing
                    ), profileMessage = null
                ) }
            } catch (e: Exception) {
                _state.update { it.copy(pendingPortableProfile = null,
                    profileMessage = "Profile import refused: invalid or unreadable JSON") }
            }
        }
    }

    fun dismissPortableImport() {
        _state.update { it.copy(pendingPortableProfile = null) }
    }

    /** Saving a portable file never invokes applyProfileSafely, downloads or file renames. */
    fun savePortableImport(name: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val preview = _state.value.pendingPortableProfile ?: return@launch
            try {
                require(ModCompatibility.fingerprint(_state.value.installedMods) ==
                    preview.inventoryFingerprint) { "Stale import preview" }
                val safeName = PortableProfileCodec.checkedName(name)
                val profile = preview.profile.copy(
                    id = UUID.randomUUID().toString(), name = safeName,
                    modifiedAt = System.currentTimeMillis(), isProtected = false
                )
                dataStore.saveProfile(profile)
                _state.update { it.copy(pendingPortableProfile = null,
                    profileMessage = "Profile metadata imported; no mods were changed") }
                loadProfiles()
            } catch (e: Exception) {
                _state.update { it.copy(profileMessage =
                    "Profile not imported: duplicate name, invalid data or changed inventory") }
            }
        }
    }

    fun saveProfileNote(profile: ModProfile, uniqueId: String, note: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val id = PortableProfileCodec.canonicalId(uniqueId.trim())
                require(note.length <= 1200 && '\u0000' !in note)
                val current = dataStore.getProfiles().single { it.id == profile.id }
                require(!current.isProtected) { "Protected" }
                val updatedNotes = current.notes.toMutableMap()
                if (note.isBlank()) updatedNotes.remove(id) else updatedNotes[id] = note
                dataStore.saveProfile(current.copy(notes = updatedNotes,
                    modifiedAt = System.currentTimeMillis()))
                _state.update { it.copy(profileMessage = "Profile note saved") }
                loadProfiles()
            } catch (e: Exception) {
                _state.update { it.copy(profileMessage = "Profile note not saved") }
            }
        }
    }

    fun previewProfile(profile: ModProfile): ModProfilePreview =
        ModCompatibility.preview(_state.value.installedMods, profile)

    fun applyProfile(profile: ModProfile, approvedFingerprint: String) {
        viewModelScope.launch(Dispatchers.IO) {
            _state.update { it.copy(isApplyingProfile = true) }
            try {
                val count = fileManager.applyProfileSafely(profile, approvedFingerprint)
                _state.update { it.copy(isApplyingProfile = false,
                    profileMessage = "Profile \"${profile.name}\" applied ($count changes)") }
                loadInstalledMods()
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to apply profile", e)
                _state.update { it.copy(isApplyingProfile = false,
                    profileMessage = "Profile not applied: ${e.message ?: "review required"}") }
                loadInstalledMods()
            }
        }
    }

    fun deleteProfile(name: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                dataStore.deleteProfile(name)
                loadProfiles()
            } catch (e: Exception) {
                _state.update { it.copy(profileMessage = "Profile deletion refused") }
            }
        }
    }

    fun clearProfileMessage() {
        _state.update { it.copy(profileMessage = null) }
    }

    private fun detectActiveProfile(profiles: List<ModProfile>): String? {
        val currentEnabled = _state.value.installedMods
            .filter { it.enabled }
            .map { it.manifest.uniqueID }
            .toSet()

        val enabledCanonical = currentEnabled.map { it.lowercase(java.util.Locale.ROOT) }.toSet()
        // Matching a loadout is informational, not proof that the user selected a profile.
        return profiles.singleOrNull {
            it.enabledModIds.map { id -> id.lowercase(java.util.Locale.ROOT) }.toSet() ==
                enabledCanonical
        }?.name
    }

    private fun updateDisplayedMods() {
        _state.update { state ->
            var mods = state.installedMods

            // Filter
            mods = when (state.filter) {
                ModFilter.ALL -> mods
                ModFilter.ENABLED -> mods.filter { it.enabled }
                ModFilter.DISABLED -> mods.filter { !it.enabled }
                ModFilter.HAS_UPDATE -> mods.filter { state.updates.containsKey(it.manifest.uniqueID) }
            }

            // Search
            if (state.searchQuery.isNotBlank()) {
                val query = state.searchQuery.lowercase()
                mods = mods.filter {
                    it.manifest.name.lowercase().contains(query) ||
                        it.manifest.author.lowercase().contains(query) ||
                        it.manifest.uniqueID.lowercase().contains(query)
                }
            }

            // Sort
            mods = when (state.sortOrder) {
                ModSortOrder.NAME -> mods.sortedBy { it.manifest.name.lowercase() }
                ModSortOrder.AUTHOR -> mods.sortedBy { it.manifest.author.lowercase() }
                ModSortOrder.STATUS -> mods.sortedWith(
                    compareByDescending<InstalledMod> { it.enabled }
                        .thenBy { it.manifest.name.lowercase() }
                )
            }

            state.copy(displayedMods = mods)
        }
    }
}
