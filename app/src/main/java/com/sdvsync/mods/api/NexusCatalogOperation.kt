package com.sdvsync.mods.api

/**
 * GraphQL filter/sort variables are typed server inputs, not post-filtered cached pages.
 * Game ID is permanently pinned to Stardew Valley (1303). All user values travel via
 * variables; never concatenate them into the GraphQL document.
 * The time threshold is provided by the caller to make tests deterministic.
 */
internal fun createNexusCatalogOperation(
    searchQuery: String,
    filters: NexusCatalogFilters = NexusCatalogFilters(),
    page: Int = 1,
    nowEpochSeconds: Long = System.currentTimeMillis() / 1000L
): NexusSearchOperation {
    val query = searchQuery.trim().take(120)
    require(query.isEmpty() || query.length >= NEXUS_MIN_SEARCH_QUERY_LENGTH)
    require(page in 1..10_000) { "Invalid Nexus catalog page" }
    val f = filters.normalized()
    val clauses = mutableListOf<Map<String, Any>>(
        mapOf("gameId" to mapOf("value" to "1303", "op" to "EQUALS"))
    )
    fun clause(field: String, value: String, op: String = "EQUALS") {
        clauses.add(mapOf(field to mapOf("value" to value, "op" to op)))
    }
    if (query.isNotEmpty()) clause("name", query, "WILDCARD")
    if (f.categoryName.isNotEmpty()) clause("categoryName", f.categoryName)
    if (f.includeTag.isNotEmpty()) clause("tag", f.includeTag)
    if (f.excludeTag.isNotEmpty()) clause("tag", f.excludeTag, "NOT_EQUALS")
    if (f.updatedWithinDays > 0) {
        clause("updatedAt", (nowEpochSeconds - f.updatedWithinDays.toLong() * 86400L).toString(), "GT")
    }
    // The provider's GT operator is strict; minimum N means > N-1.
    if (f.minDownloads > 0) clause("downloads", (f.minDownloads - 1).toString(), "GT")
    if (f.minEndorsements > 0) clause("endorsements", (f.minEndorsements - 1).toString(), "GT")
    return NexusSearchOperation(
        document = """
            query CinderboxCatalog(${'$'}filter: ModsFilter!, ${'$'}sort: [ModsSort!], ${'$'}offset: Int!) {
              mods(filter: ${'$'}filter, sort: ${'$'}sort, offset: ${'$'}offset, count: $NEXUS_SEARCH_PAGE_SIZE) {
                nodes {
                  modId
                  name
                  summary
                  author
                  pictureUrl
                  endorsementCount: endorsements
                  modDownloadCount: downloads
                  version
                  categoryName: category
                }
                totalCount
              }
            }
        """.trimIndent(),
        variables = mapOf(
            "filter" to mapOf("filter" to clauses, "op" to "AND"),
            "sort" to listOf(mapOf(f.sort.wireName to mapOf("direction" to if (f.sort == NexusCatalogSort.NAME) "ASC" else "DESC"))),
            "offset" to (page - 1) * NEXUS_SEARCH_PAGE_SIZE
        )
    )
}
