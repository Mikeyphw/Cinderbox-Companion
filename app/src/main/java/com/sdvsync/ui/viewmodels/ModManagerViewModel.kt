package com.sdvsync.ui.viewmodels

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sdvsync.cinderbox.CinderboxLayoutEvents
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.ModDataStore
import com.sdvsync.mods.ModFileManager
import com.sdvsync.mods.ModArchivePreview
import com.sdvsync.mods.ModReviewQueue
import com.sdvsync.mods.ModSnapshot
import com.sdvsync.mods.api.SmapiUpdateChecker
import com.sdvsync.mods.models.InstallResult
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModProfile
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
    val profileMessage: String? = null
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
                val updates = dataStore.getUpdateCache()
                _state.update {
                    it.copy(installedMods = mods, updates = updates, isLoading = false)
                }
                updateDisplayedMods()
                loadProfiles()
                refreshSafetyState()

                // Auto-check for updates if stale
                val lastCheck = dataStore.getLastUpdateCheck()
                if (mods.isNotEmpty() && System.currentTimeMillis() - lastCheck > UPDATE_CHECK_INTERVAL_MS) {
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

                // Cache the results
                dataStore.setUpdateCache(updates)

                _state.update { it.copy(updates = updates, isCheckingUpdates = false) }
                updateDisplayedMods()
            } catch (e: Exception) {
                AppLogger.e(TAG, "Update check failed", e)
                _state.update { it.copy(isCheckingUpdates = false) }
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
                val activeName = detectActiveProfile(profiles)
                _state.update { it.copy(profiles = profiles, activeProfileName = activeName) }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to load profiles", e)
            }
        }
    }

    fun saveCurrentAsProfile(name: String) {
        viewModelScope.launch(Dispatchers.IO) {
            val enabledIds = _state.value.installedMods
                .filter { it.enabled }
                .map { it.manifest.uniqueID }
                .toSet()

            val profile = ModProfile(name = name, enabledModIds = enabledIds)
            dataStore.saveProfile(profile)

            val profiles = dataStore.getProfiles()
            _state.update {
                it.copy(
                    profiles = profiles,
                    activeProfileName = name,
                    profileMessage = "Profile \"$name\" saved"
                )
            }
        }
    }

    fun applyProfile(profile: ModProfile) {
        viewModelScope.launch(Dispatchers.IO) {
            _state.update { it.copy(isApplyingProfile = true) }
            try {
                val mods = _state.value.installedMods
                for (mod in mods) {
                    val shouldEnable = mod.manifest.uniqueID in profile.enabledModIds
                    if (mod.enabled != shouldEnable) {
                        if (shouldEnable) {
                            fileManager.enableMod(mod.folderName)
                        } else {
                            fileManager.disableMod(mod.folderName)
                        }
                    }
                }
                _state.update {
                    it.copy(
                        isApplyingProfile = false,
                        profileMessage = "Profile \"${profile.name}\" applied"
                    )
                }
                loadInstalledMods()
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to apply profile", e)
                _state.update {
                    it.copy(isApplyingProfile = false, profileMessage = "Failed to apply profile")
                }
            }
        }
    }

    fun deleteProfile(name: String) {
        viewModelScope.launch(Dispatchers.IO) {
            dataStore.deleteProfile(name)
            loadProfiles()
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

        return profiles.find { it.enabledModIds == currentEnabled }?.name
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
