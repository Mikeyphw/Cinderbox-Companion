package com.sdvsync.ui.viewmodels

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sdvsync.R
import com.sdvsync.logging.AppLogger
import com.sdvsync.mods.ModDataStore
import com.sdvsync.mods.ModFileManager
import com.sdvsync.mods.ModMetadata
import com.sdvsync.mods.api.NEXUS_MIN_SEARCH_QUERY_LENGTH
import com.sdvsync.mods.api.NexusModSource
import com.sdvsync.mods.api.NexusCatalogFilters
import com.sdvsync.mods.api.NexusCatalogSort
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.RemoteMod
import java.util.Locale
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class BrowseCategory {
    TRENDING,
    LATEST,
    RECENTLY_UPDATED
}

data class ModBrowseState(
    val hasApiKey: Boolean = false,
    val isValidatingKey: Boolean = false,
    @StringRes val apiKeyErrorRes: Int? = null,
    val category: BrowseCategory = BrowseCategory.TRENDING,
    val searchQuery: String = "",
    val filters: NexusCatalogFilters = NexusCatalogFilters(),
    val totalResults: Int = 0,
    val mods: List<RemoteMod> = emptyList(),
    val installedSourceIds: Set<String> = emptySet(),
    val isLoading: Boolean = false,
    val page: Int = 0,
    val hasMore: Boolean = false,
    val isLoadingMore: Boolean = false,
    val loadMoreError: NexusUiError? = null,
    val searchNeedsMoreCharacters: Boolean = false,
    val error: NexusUiError? = null
)

internal class BrowseRequestGate {
    private var generation = 0L

    fun next(): Long = ++generation

    fun current(): Long = generation

    fun isCurrent(requestGeneration: Long): Boolean = generation == requestGeneration
}

internal fun remoteModSourceIdentifier(sourceId: String, modId: String): String =
    "${sourceId.trim()}:${modId.trim()}".lowercase(Locale.ROOT)

internal fun collectInstalledSourceIds(
    installedMods: List<InstalledMod>,
    metadata: Map<String, ModMetadata>
): Set<String> {
    val metadataByUniqueId = metadata.mapKeys { (uniqueId, _) -> uniqueId.lowercase(Locale.ROOT) }
    return installedMods.mapNotNullTo(mutableSetOf()) { installedMod ->
        metadataByUniqueId[installedMod.manifest.uniqueID.lowercase(Locale.ROOT)]
            ?.installedFrom
            ?.trim()
            ?.takeIf(String::isNotEmpty)
            ?.lowercase(Locale.ROOT)
    }
}

internal fun mergeSearchPages(current: List<RemoteMod>, next: List<RemoteMod>): List<RemoteMod> {
    val seen = current.mapTo(mutableSetOf()) { remoteModSourceIdentifier(it.sourceId, it.modId) }
    return buildList {
        addAll(current)
        next.forEach { mod ->
            if (seen.add(remoteModSourceIdentifier(mod.sourceId, mod.modId))) add(mod)
        }
    }
}

internal fun searchNeedsMoreCharacters(query: String): Boolean {
    val normalizedQuery = query.trim()
    return normalizedQuery.isNotEmpty() && normalizedQuery.length < NEXUS_MIN_SEARCH_QUERY_LENGTH
}

class ModBrowseViewModel(
    private val nexusSource: NexusModSource,
    private val dataStore: ModDataStore,
    private val fileManager: ModFileManager
) : ViewModel() {

    companion object {
        private const val TAG = "ModBrowseVM"
    }

    private val _state = MutableStateFlow(ModBrowseState())
    val state: StateFlow<ModBrowseState> = _state.asStateFlow()

    private var browseJob: Job? = null
    private val requestGate = BrowseRequestGate()

    init {
        viewModelScope.launch {
            val saved = try { dataStore.getNexusCatalogFilters() }
                catch (e: CancellationException) { throw e }
                catch (_: Exception) { NexusCatalogFilters() }
            _state.update { it.copy(filters = saved) }
            checkApiKey()
        }
        loadInstalledSourceIds()
    }

    private fun checkApiKey() {
        val hasApiKey = !dataStore.getNexusApiKey().isNullOrBlank()
        _state.value = _state.value.copy(hasApiKey = hasApiKey)
        if (hasApiKey) {
            requestCatalog("", _state.value.filters, _state.value.category, debounce = false)
        }
    }

    private fun loadInstalledSourceIds() {
        viewModelScope.launch(Dispatchers.IO) {
            val installedMods = fileManager.listInstalledMods()
            val metadata = dataStore.getAllModMetadata()
            _state.update {
                it.copy(installedSourceIds = collectInstalledSourceIds(installedMods, metadata))
            }
        }
    }

    fun validateAndSaveApiKey(key: String) {
        val normalizedKey = key.trim()
        if (normalizedKey.isEmpty()) return

        viewModelScope.launch {
            _state.update { it.copy(isValidatingKey = true, apiKeyErrorRes = null) }
            try {
                val valid = nexusSource.validateApiKey(normalizedKey)
                if (valid) {
                    dataStore.setNexusApiKey(normalizedKey)
                    _state.update { it.copy(hasApiKey = true, isValidatingKey = false) }
                    loadCategory(BrowseCategory.TRENDING)
                } else {
                    _state.update {
                        it.copy(
                            isValidatingKey = false,
                            apiKeyErrorRes = R.string.mods_api_key_invalid
                        )
                    }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "API key validation failed", e)
                _state.update {
                    it.copy(
                        isValidatingKey = false,
                        apiKeyErrorRes = classifyNexusError(
                            e,
                            R.string.mods_api_key_validation_failed
                        ).messageRes
                    )
                }
            }
        }
    }

    fun removeApiKey() {
        requestGate.next()
        browseJob?.cancel()
        browseJob = null
        dataStore.setNexusApiKey(null)
        viewModelScope.launch { dataStore.setNexusCatalogFilters(NexusCatalogFilters()) }
        _state.value = _state.value.copy(
            hasApiKey = false,
            isValidatingKey = false,
            apiKeyErrorRes = null,
            searchQuery = "",
            totalResults = 0,
            filters = NexusCatalogFilters(),
            mods = emptyList(),
            isLoading = false,
            page = 0,
            hasMore = false,
            isLoadingMore = false,
            loadMoreError = null,
            searchNeedsMoreCharacters = false,
            error = null
        )
    }

    fun loadCategory(category: BrowseCategory) {
        val current = _state.value
        val sort = when (category) {
            BrowseCategory.TRENDING -> NexusCatalogSort.ENDORSEMENTS
            BrowseCategory.LATEST -> NexusCatalogSort.NEWEST
            BrowseCategory.RECENTLY_UPDATED -> NexusCatalogSort.UPDATED
        }
        val updated = current.filters.copy(sort = sort)
        requestCatalog("", updated, category, debounce = false)
        viewModelScope.launch {
            try { dataStore.setNexusCatalogFilters(updated) }
            catch (e: CancellationException) { throw e }
            catch (e: Exception) { AppLogger.e(TAG, "Unable to save Nexus sort", e) }
        }
    }

    /** Every refinement creates a fresh first-page API request. Never filter a partial page. */
    fun applyFilters(filters: NexusCatalogFilters) {
        val current = _state.value
        val normalized = filters.normalized()
        requestCatalog(current.searchQuery, normalized, current.category, debounce = false)
        viewModelScope.launch {
            try { dataStore.setNexusCatalogFilters(normalized) }
            catch (e: CancellationException) { throw e }
            catch (e: Exception) { AppLogger.e(TAG, "Unable to save Nexus filters", e) }
        }
    }

    fun search(query: String) {
        val current = _state.value
        requestCatalog(query, current.filters, current.category, debounce = true)
    }

    private fun requestCatalog(
        query: String,
        filters: NexusCatalogFilters,
        category: BrowseCategory,
        debounce: Boolean
    ) {
        val normalized = query.trim()
        val needsMore = searchNeedsMoreCharacters(query)
        val generation = beginBrowseRequest()
        _state.value = _state.value.copy(
            category = category, filters = filters, searchQuery = query,
            mods = emptyList(), totalResults = 0,
            isLoading = !needsMore, page = 0, hasMore = false,
            isLoadingMore = false, loadMoreError = null,
            searchNeedsMoreCharacters = needsMore, error = null
        )
        if (needsMore) return
        browseJob = viewModelScope.launch {
            if (debounce && normalized.isNotEmpty()) delay(300)
            try {
                val result = nexusSource.browse(normalized, filters = filters, page = 1)
                updateIfCurrent(generation) {
                    it.copy(mods = result.mods, totalResults = result.totalResults,
                        isLoading = false, page = 1, hasMore = result.hasMore)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Nexus catalog failed", e)
                updateIfCurrent(generation) {
                    it.copy(isLoading = false,
                        error = classifyNexusError(e, R.string.mods_error_search_failed))
                }
            }
        }
    }

    fun loadMore() {
        val current = _state.value
        if (current.isLoading || current.isLoadingMore || !current.hasMore ||
            current.searchNeedsMoreCharacters) return
        val generation = requestGate.current()
        val nextPage = current.page + 1
        if (nextPage > 10_000) return
        _state.update { it.copy(isLoadingMore = true, loadMoreError = null) }
        browseJob = viewModelScope.launch {
            try {
                val result = nexusSource.browse(current.searchQuery.trim(),
                    filters = current.filters, page = nextPage)
                updateIfCurrent(generation) {
                    it.copy(mods = mergeSearchPages(it.mods, result.mods),
                        totalResults = result.totalResults,
                        page = nextPage, hasMore = result.hasMore,
                        isLoadingMore = false, loadMoreError = null)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to load more Nexus results", e)
                updateIfCurrent(generation) {
                    it.copy(isLoadingMore = false,
                        loadMoreError = classifyNexusError(e, R.string.mods_error_load_more_failed))
                }
            }
        }
    }

    fun retry() {
        val current = _state.value
        requestCatalog(current.searchQuery, current.filters, current.category, debounce = false)
    }

    private fun beginBrowseRequest(): Long {
        val requestGeneration = requestGate.next()
        browseJob?.cancel()
        browseJob = null
        return requestGeneration
    }

    private inline fun updateIfCurrent(requestGeneration: Long, transform: (ModBrowseState) -> ModBrowseState) {
        if (requestGate.isCurrent(requestGeneration)) {
            _state.update(transform)
        }
    }
}
