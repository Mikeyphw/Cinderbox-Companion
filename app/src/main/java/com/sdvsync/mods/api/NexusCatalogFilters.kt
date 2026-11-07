package com.sdvsync.mods.api

/** Read-only provider discovery controls. No account/installation authority. */
enum class NexusCatalogSort(val wireName: String, val label: String) {
    ENDORSEMENTS("endorsements", "Most endorsed"),
    DOWNLOADS("downloads", "Most downloaded"),
    UPDATED("updatedAt", "Recently updated"),
    NEWEST("createdAt", "Newest"),
    NAME("name", "Name")
}

data class NexusCatalogFilters(
    val categoryName: String = "",
    val includeTag: String = "",
    val excludeTag: String = "",
    val updatedWithinDays: Int = 0,
    val minDownloads: Int = 0,
    val minEndorsements: Int = 0,
    val sort: NexusCatalogSort = NexusCatalogSort.ENDORSEMENTS
) {
    fun normalized(): NexusCatalogFilters = copy(
        categoryName = categoryName.trim().take(64),
        includeTag = includeTag.trim().take(64),
        excludeTag = excludeTag.trim().take(64),
        updatedWithinDays = updatedWithinDays.coerceIn(0, 3650),
        minDownloads = minDownloads.coerceIn(0, 10_000_000),
        minEndorsements = minEndorsements.coerceIn(0, 1_000_000)
    )

    val hasRefinements: Boolean get() = categoryName.isNotBlank() ||
        includeTag.isNotBlank() || excludeTag.isNotBlank() || updatedWithinDays != 0 ||
        minDownloads != 0 || minEndorsements != 0 || sort != NexusCatalogSort.ENDORSEMENTS
}
