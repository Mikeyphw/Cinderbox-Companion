package com.sdvsync.ui.screens

import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.sdvsync.mods.models.RemoteMod
import com.sdvsync.mods.api.NexusCatalogFilters
import com.sdvsync.mods.api.NexusCatalogSort
import com.sdvsync.mods.api.NexR2Display
import com.sdvsync.mods.api.NexusIdJumpPolicy
import com.sdvsync.ui.components.CinderboxBrandTopBar
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.BrowseCategory
import com.sdvsync.ui.viewmodels.ModBrowseViewModel
import com.sdvsync.ui.viewmodels.ModManagerViewModel
import com.sdvsync.ui.viewmodels.NexusErrorAction
import com.sdvsync.ui.viewmodels.remoteModSourceIdentifier
import org.json.JSONArray
import org.json.JSONObject
import org.koin.androidx.compose.koinViewModel

/**
 * UX-05: real, native, single-dark Mods experience. Discover is powered by the
 * existing Nexus browse provider; no fake listings, permissions, or Steam login.
 * Local metadata-only bookmarks never modify mod folders. Actual installation,
 * bulk changes, and profile application remain in the existing reviewed flows.
 */
private enum class ModsPane(val label: String) {
    DISCOVER("Discover"), INSTALLED("Installed"), UPDATES("Updates"), PROFILES("Profiles")
}
private enum class DiscoverFilter(val label: String) {
    ALL("All"), INSTALLED("Installed"), SAVED("Saved")
}

private data class ModCardData(
    val sourceId: String,
    val modId: String,
    val name: String,
    val author: String,
    val version: String,
    val categoryName: String?,
    val pictureUrl: String?,
    val summary: String = "",
    val endorsements: Int = 0,
    val downloads: Int = 0,
    val lastUpdated: Long = 0
) {
    val id: String get() = remoteModSourceIdentifier(sourceId, modId)
}

private fun RemoteMod.asCard(): ModCardData = ModCardData(
    sourceId, modId, NexR2Display.text(name, 120), NexR2Display.text(author, 80),
    NexR2Display.text(version, 32), categoryName?.let { NexR2Display.text(it, 60) },
    NexR2Display.imageUrl(pictureUrl), NexR2Display.text(summary, 180),
    endorsements.coerceAtLeast(0), downloads.coerceAtLeast(0), lastUpdated)

/** Bounded on-device metadata only; no mod file/archive content or API keys. */
private fun readSavedCards(raw: String?): Map<String, ModCardData> = runCatching {
    val arr = JSONArray(raw ?: "[]")
    val found = linkedMapOf<String, ModCardData>()
    for (i in 0 until minOf(arr.length(), 256)) {
        val item = arr.optJSONObject(i) ?: continue
        val source = item.optString("source").take(40)
        val id = item.optString("id").take(80)
        if (source.isBlank() || id.isBlank()) continue
        val card = ModCardData(source, id, item.optString("name").take(120),
            item.optString("author").take(80), item.optString("version").take(32),
            item.optString("category").take(60).ifBlank { null },
            NexR2Display.imageUrl(item.optString("picture")),
            NexR2Display.text(item.optString("summary"), 180),
            item.optInt("endorsements", 0).coerceAtLeast(0),
            item.optInt("downloads", 0).coerceAtLeast(0),
            item.optLong("lastUpdated", 0L))
        found[card.id] = card
    }
    found.toMap()
}.getOrDefault(emptyMap())

private fun savedCardsJson(cards: Collection<ModCardData>): String = JSONArray().apply {
    cards.take(256).forEach { card ->
        put(JSONObject().apply {
            put("source", card.sourceId)
            put("id", card.modId)
            put("name", card.name)
            put("author", card.author)
            put("version", card.version)
            put("category", card.categoryName ?: "")
            put("picture", NexR2Display.imageUrl(card.pictureUrl) ?: "")
            put("summary", NexR2Display.text(card.summary, 180))
            put("endorsements", card.endorsements.coerceAtLeast(0))
            put("downloads", card.downloads.coerceAtLeast(0))
            put("lastUpdated", card.lastUpdated)
        })
    }
}.toString()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovedModsScreen(
    onBrowseMods: () -> Unit,
    onOpenRemoteMod: (String, String) -> Unit,
    onOpenInstalledMod: (String) -> Unit,
    onOpenAdvancedMods: () -> Unit,
    onOpenQueue: () -> Unit = {},
    onOpenProfileDetail: (String) -> Unit = {},
    viewModel: ModManagerViewModel = koinViewModel(),
    browseViewModel: ModBrowseViewModel = koinViewModel(),
    onOpenOperationCenter: () -> Unit = {},
    onOpenExactNexusSelection: (String, String) -> Unit = { _, _ -> }
) {
    val state by viewModel.state.collectAsState()
    val browse by browseViewModel.state.collectAsState()
    val ctx = LocalContext.current
    // Persist only public provider/mod identifiers, never account data or API keys.
    val bookmarks = androidx.compose.runtime.remember(ctx) {
        ctx.getSharedPreferences("ux05_mod_bookmarks", Context.MODE_PRIVATE)
    }
    var savedCards by androidx.compose.runtime.remember(bookmarks) {
        mutableStateOf(readSavedCards(bookmarks.getString("cards", null)))
    }
    androidx.lifecycle.compose.LifecycleResumeEffect(bookmarks) {
        savedCards = readSavedCards(bookmarks.getString("cards", null))
        onPauseOrDispose {}
    }
    val savedIds = savedCards.keys
    // Always available from Mods: no catalogue search or numeric-result guessing.
    var idLookupOpen by rememberSaveable { mutableStateOf(false) }
    var idLookupMod by rememberSaveable { mutableStateOf("") }
    var idLookupFile by rememberSaveable { mutableStateOf("") }
    val idLookupTarget = NexusIdJumpPolicy.parse(idLookupMod, idLookupFile)
    if (idLookupOpen) {
        ModalBottomSheet(onDismissRequest = { idLookupOpen = false },
            containerColor = Dark.Paper, contentColor = Dark.Ink) {
            Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp).padding(bottom = 28.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Open by Nexus ID", style = MaterialTheme.typography.titleLarge)
                Text("Jump straight to a Stardew Valley mod and optionally one exact file.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                OutlinedTextField(value = idLookupMod,
                    onValueChange = { idLookupMod = it.take(24) },
                    label = { Text("Mod ID") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth().testTag("cbnx01.id-lookup.mod"))
                OutlinedTextField(value = idLookupFile,
                    onValueChange = { idLookupFile = it.take(24) },
                    label = { Text("File ID (optional)") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth().testTag("cbnx01.id-lookup.file"))
                if (idLookupTarget == null && (idLookupMod.isNotBlank() || idLookupFile.isNotBlank())) {
                    Text("Use positive decimal IDs of at most 12 digits; no leading zeros.",
                        color = Dark.Warn, style = MaterialTheme.typography.bodySmall)
                }
                if (!browse.hasApiKey) Text("Nexus access is needed to load live mod and file data.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Button(enabled = idLookupTarget != null,
                    modifier = Modifier.fillMaxWidth().testTag("cbnx01.id-lookup.open"),
                    onClick = {
                        idLookupTarget?.let { target ->
                            idLookupOpen = false
                            if (target.fileId == null) onOpenRemoteMod(target.modId, "nexus")
                            else onOpenExactNexusSelection(target.modId, target.fileId)
                        }
                    }) { Text("Open exact selection") }
                Text("Opening details never starts a download or installs a mod.",
                    color = Dark.Muted, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
    var pane by rememberSaveable { mutableStateOf(ModsPane.DISCOVER) }
    var filter by rememberSaveable { mutableStateOf(DiscoverFilter.ALL) }
    var gridMode by rememberSaveable { mutableStateOf(true) }
    var filterOpen by rememberSaveable { mutableStateOf(false) }
    // Source-bound local bookmark identity only; no remote mod route when offline.
    var offlineSavedId by rememberSaveable { mutableStateOf<String?>(null) }
    var installedOrder by rememberSaveable { mutableStateOf(0) }
    val bookmarkToggle: (ModCardData) -> Unit = { mod ->
        val next = if (mod.id in savedIds) savedCards - mod.id
                   else (savedCards + (mod.id to mod)).entries.toList().takeLast(256)
                       .associate { it.key to it.value }
        bookmarks.edit().putString("cards", savedCardsJson(next.values)).apply()
        savedCards = next
    }

    // A saved card must be inspectable even without credentials. This sheet
    // shows ONLY bounded local bookmark metadata, never file/install claims.
    val offlineSavedCard = offlineSavedId?.let { savedCards[it] }
    if (offlineSavedCard != null && !browse.hasApiKey) {
        ModalBottomSheet(
            onDismissRequest = { offlineSavedId = null },
            containerColor = Dark.Paper, contentColor = Dark.Ink
        ) {
            Column(Modifier.fillMaxWidth().testTag("nex.r4.offline-saved-detail")
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp).padding(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Saved mod · offline", style = MaterialTheme.typography.titleMedium)
                Text(offlineSavedCard.name, color = Dark.Ink,
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.testTag("nex.r4.offline-title"))
                Text("by " + offlineSavedCard.author, color = Dark.Muted)
                offlineSavedCard.categoryName?.takeIf { it.isNotBlank() }?.let {
                    Text(it, color = Dark.Forest)
                }
                if (offlineSavedCard.version.isNotBlank()) {
                    Text("Version " + offlineSavedCard.version, color = Dark.Muted)
                }
                if (offlineSavedCard.summary.isNotBlank()) {
                    Text(offlineSavedCard.summary, color = Dark.Ink)
                }
                Text("Saved metadata only. Live details, files and downloads require Nexus access.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Button(onClick = onBrowseMods, modifier = Modifier.fillMaxWidth()
                    .testTag("nex.r4.configure-nexus")) { Text("Configure Nexus access") }
                OutlinedButton(onClick = { offlineSavedId = null },
                    modifier = Modifier.fillMaxWidth().testTag("nex.r4.offline-close")) {
                    Text("Close")
                }
            }
        }
    }

    // Local-only selections are explicit; all provider refinements are sent to Nexus.
    var draftCategory by rememberSaveable { mutableStateOf("") }
    var draftIncludeTag by rememberSaveable { mutableStateOf("") }
    var draftExcludeTag by rememberSaveable { mutableStateOf("") }
    var draftDays by rememberSaveable { mutableStateOf(0) }
    var draftDownloads by rememberSaveable { mutableStateOf(0) }
    var draftEndorsements by rememberSaveable { mutableStateOf(0) }
    var draftSort by rememberSaveable { mutableStateOf(NexusCatalogSort.ENDORSEMENTS.name) }

    if (filterOpen) {
        ModalBottomSheet(onDismissRequest = { filterOpen = false },
            containerColor = Dark.Paper, contentColor = Dark.Ink) {
            Column(Modifier.fillMaxWidth().testTag("nex.r1.filter.sheet")
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp).padding(bottom = 25.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Refine discovery", style = MaterialTheme.typography.titleLarge)
                Text("Nexus catalog filters · all matching mods", color = Dark.Muted)
                Text("Sort by", color = Dark.Muted)
                NexusCatalogSort.entries.forEach { option ->
                    ModsChoice(option.label, draftSort == option.name) { draftSort = option.name }
                }
                OutlinedTextField(value = draftCategory, onValueChange = { draftCategory = it.take(64) },
                    label = { Text("Category (exact Nexus name)") },
                    modifier = Modifier.fillMaxWidth().testTag("nex.r1.filter.category"), singleLine = true)
                val suggestedCategories = browse.mods.mapNotNull { it.categoryName?.takeIf(String::isNotBlank) }
                    .distinct().sorted().take(8)
                if (suggestedCategories.isNotEmpty()) {
                    Text("Suggestions from loaded cards, not the full category list", color = Dark.Muted,
                        style = MaterialTheme.typography.bodySmall)
                    suggestedCategories.forEach { suggestion ->
                        ModsChoice(suggestion, draftCategory == suggestion) { draftCategory = suggestion }
                    }
                }
                OutlinedTextField(value = draftIncludeTag,
                    onValueChange = { draftIncludeTag = it.take(64) },
                    label = { Text("Include tag") }, modifier = Modifier.fillMaxWidth()
                        .testTag("nex.r1.filter.include-tag"), singleLine = true)
                OutlinedTextField(value = draftExcludeTag,
                    onValueChange = { draftExcludeTag = it.take(64) },
                    label = { Text("Exclude tag (e.g. Translation)") },
                    modifier = Modifier.fillMaxWidth().testTag("nex.r1.filter.exclude-tag"),
                    singleLine = true)
                Text("Updated within", color = Dark.Muted)
                listOf(0 to "Any time", 7 to "7 days", 30 to "30 days", 365 to "1 year").forEach { (days, label) ->
                    ModsChoice(label, draftDays == days) { draftDays = days }
                }
                Text("Minimum downloads", color = Dark.Muted)
                listOf(0, 100, 1000, 10000).forEach { count ->
                    ModsChoice(if (count == 0) "Any" else "$count+", draftDownloads == count) {
                        draftDownloads = count
                    }
                }
                Text("Minimum endorsements", color = Dark.Muted)
                listOf(0, 10, 100, 1000).forEach { count ->
                    ModsChoice(if (count == 0) "Any" else "$count+", draftEndorsements == count) {
                        draftEndorsements = count
                    }
                }
                Text("Only on loaded results", color = Dark.Muted)
                DiscoverFilter.entries.forEach { option ->
                    ModsChoice(option.label, filter == option) { filter = option }
                }
                OutlinedButton(onClick = {
                    draftCategory = ""; draftIncludeTag = ""; draftExcludeTag = ""
                    draftDays = 0; draftDownloads = 0; draftEndorsements = 0
                    draftSort = NexusCatalogSort.ENDORSEMENTS.name
                }, modifier = Modifier.fillMaxWidth().testTag("nex.r1.filter.clear")) {
                    Text("Clear provider filters")
                }
                Button(onClick = {
                    browseViewModel.applyFilters(NexusCatalogFilters(
                        categoryName = draftCategory, includeTag = draftIncludeTag,
                        excludeTag = draftExcludeTag, updatedWithinDays = draftDays,
                        minDownloads = draftDownloads, minEndorsements = draftEndorsements,
                        sort = NexusCatalogSort.valueOf(draftSort)))
                    filterOpen = false
                }, modifier = Modifier.fillMaxWidth().testTag("nex.r1.filter.apply")) {
                    Text("Apply filters to Nexus")
                }
            }
        }
    }

    // The Saved view is independent of the currently loaded Nexus category.
    val cardsFromProvider = browse.mods.map { it.asCard() }
    val browseCandidates = if (filter == DiscoverFilter.SAVED)
        savedCards.values.toList() else cardsFromProvider
    val visibleBrowse = browseCandidates.filter { mod ->
        when (filter) {
            DiscoverFilter.ALL -> true
            DiscoverFilter.INSTALLED -> mod.id in browse.installedSourceIds
            DiscoverFilter.SAVED -> mod.id in savedIds
        }
    }
    val installedMods = when (installedOrder) {
        1 -> state.installedMods.sortedBy { it.manifest.author.lowercase(java.util.Locale.ROOT) }
        2 -> state.installedMods.sortedBy { if (it.enabled) 0 else 1 }
        else -> state.installedMods.sortedBy { it.manifest.name.lowercase(java.util.Locale.ROOT) }
    }

    // Retain LazyListState (including its Saver) while returning from mod details.
    val discoverScroll = rememberLazyListState()
    LazyColumn(
        state = discoverScroll,
        modifier = Modifier.fillMaxSize().background(Dark.Background)
            .testTag("cinderbox.screen.mods"),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(
            start = 18.dp, end = 18.dp, top = 18.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            CinderboxBrandTopBar(
                subtitle = "YOUR MOD LIBRARY",
                onOpenOperationCenter = onOpenOperationCenter
            )
        }
        item {
            Column {
                Text("MAKE IT YOUR VALLEY", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold, letterSpacing = 1.1.sp))
                Spacer(Modifier.height(5.dp))
                Text("Mods", color = Dark.Ink,
                    style = MaterialTheme.typography.headlineMedium.copy(
                        fontWeight = FontWeight.Bold, fontSize = 25.sp),
                    modifier = Modifier.semantics { heading() })
                Text("Discover, organize and customize.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = onOpenQueue,
                    modifier = Modifier.testTag("cinderbox.mods.download-queue")
                        .semantics { contentDescription = "Open mod download queue" }) {
                    Text("Download queue", color = Dark.Forest)
                }
            }
        }
        item { ModsPaneSelector(pane) { pane = it } }
        // Fast source-ID entry is independent of catalogue sorting and loaded pages.
        item {
            OutlinedButton(onClick = { idLookupOpen = true },
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                    .testTag("cbnx01.mods.open-by-id"),
                shape = RoundedCornerShape(12.dp)) { Text("Open by Nexus ID") }
        }
        // Always-visible entry point, independent of Nexus listings or category.
        item {
            OutlinedButton(
                onClick = onOpenAdvancedMods,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                    .testTag("cinderbox.mods.advanced"),
                shape = RoundedCornerShape(12.dp)
            ) { Text("Manage local mods") }
        }
        if (pane != ModsPane.DISCOVER) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ModsSummary("INSTALLED", state.installedMods.size.toString(), Modifier.weight(1f))
                    ModsSummary("UPDATES", state.updates.size.toString(), Modifier.weight(1f))
                    ModsSummary("PROFILES", state.profiles.size.toString(), Modifier.weight(1f))
                }
            }
        }
        when (pane) {
            ModsPane.DISCOVER -> {
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        OutlinedTextField(
                            value = browse.searchQuery,
                            onValueChange = { browseViewModel.search(it) },
                            enabled = browse.hasApiKey,
                            modifier = Modifier.weight(1f).testTag("cinderbox.mods.search"),
                            placeholder = { Text("Search mods or authors…") },
                            singleLine = true,
                            isError = browse.searchNeedsMoreCharacters,
                            supportingText = if (browse.searchNeedsMoreCharacters) {
                                { Text("Enter more characters to search") }
                            } else null
                        )
                        OutlinedButton(onClick = {
                            val f = browse.filters
                            draftCategory = f.categoryName
                            draftIncludeTag = f.includeTag
                            draftExcludeTag = f.excludeTag
                            draftDays = f.updatedWithinDays
                            draftDownloads = f.minDownloads
                            draftEndorsements = f.minEndorsements
                            draftSort = f.sort.name
                            filterOpen = true
                        },
                            modifier = Modifier.heightIn(min = 48.dp).testTag("cinderbox.mods.filter")) {
                            Text("Refine")
                        }
                    }
                }
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf(BrowseCategory.TRENDING to "Trending",
                            BrowseCategory.LATEST to "New",
                            BrowseCategory.RECENTLY_UPDATED to "Updated").forEach { (category,label) ->
                            ModsSmallChip(label, browse.category == category && browse.searchQuery.isBlank()) {
                                browseViewModel.loadCategory(category)
                                filter = DiscoverFilter.ALL
                            }
                        }
                        ModsSmallChip("Saved", filter == DiscoverFilter.SAVED) {
                            filter = if (filter == DiscoverFilter.SAVED) DiscoverFilter.ALL else DiscoverFilter.SAVED
                        }
                    }
                }
                item {
                    ModsPanel("Made for your farm",
                        "Explore visual packs, expansions and utilities. Compatibility requires evidence from the source.") {
                        Text("Expansions  ·  Quality of life  ·  Visuals", color = Dark.Forest,
                            style = MaterialTheme.typography.labelMedium)
                    }
                }
                item {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Browse mods", color = Dark.Ink, style = MaterialTheme.typography.titleMedium)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val resultsLabel = if (filter != DiscoverFilter.ALL) "${visibleBrowse.size} local"
                                else if (browse.totalResults > 0) "${visibleBrowse.size}/${browse.totalResults} matches"
                                else if (browse.mods.isNotEmpty()) "${visibleBrowse.size} shown · total unavailable"
                                else "0 matches"
                            Text(resultsLabel, color = Dark.Muted,
                                style = MaterialTheme.typography.bodySmall)
                            TextButton(onClick = { gridMode = !gridMode },
                                modifier = Modifier.testTag("cinderbox.mods.layout")) {
                                Text(if (gridMode) "List" else "Grid")
                            }
                        }
                    }
                }
                if (browse.filters.hasRefinements && filter != DiscoverFilter.SAVED) {
                    item {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Text("Server filters active", color = Dark.Muted, modifier = Modifier.weight(1f))
                            TextButton(onClick = {
                                browseViewModel.applyFilters(NexusCatalogFilters())
                            }, modifier = Modifier.testTag("nex.r1.filters.clear-active")) {
                                Text("Clear all")
                            }
                        }
                    }
                }
                if (!browse.hasApiKey && filter != DiscoverFilter.SAVED) {
                    item {
                        ModsPanel("Nexus connection required",
                            "Add a Nexus API key to browse community listings. Steam is not required.") {
                            Button(onClick = onBrowseMods, modifier = Modifier.fillMaxWidth()) {
                                Text("Configure Nexus access")
                            }
                        }
                    }
                } else if (browse.isLoading && filter != DiscoverFilter.SAVED) {
                    item { ModsPanel("Loading community mods", "Retrieving metadata from Nexus Mods.") }
                } else if (browse.error != null && filter != DiscoverFilter.SAVED) {
                    item {
                        ModsPanel("Mod catalog unavailable",
                            androidx.compose.ui.res.stringResource(browse.error!!.messageRes)) {
                            when (browse.error!!.action) {
                                NexusErrorAction.RETRY -> Button(onClick = browseViewModel::retry) { Text("Retry") }
                                NexusErrorAction.REPLACE_API_KEY -> Button(onClick = onBrowseMods) { Text("Manage Nexus access") }
                                NexusErrorAction.NONE -> Unit
                            }
                        }
                    }
                } else if (browse.searchNeedsMoreCharacters && filter != DiscoverFilter.SAVED) {
                    item { ModsPanel("Keep typing", "Nexus search needs a longer query.") }
                } else if (visibleBrowse.isEmpty()) {
                    item { ModsPanel("No matching mods", "Try another filter, search, or category. No installed mods were changed.") }
                } else {
                    val rows = if (gridMode) visibleBrowse.chunked(2) else visibleBrowse.map { listOf(it) }
                    items(rows.size) { rowIndex ->
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            rows[rowIndex].forEach { mod ->
                                val id = remoteModSourceIdentifier(mod.sourceId, mod.modId)
                                RemoteModCard(mod = mod, saved = id in savedIds,
                                    isInstalled = id in browse.installedSourceIds,
                                    compact = !gridMode,
                                    offlineMetadataOnly = filter == DiscoverFilter.SAVED && !browse.hasApiKey,
                                    modifier = Modifier.weight(1f),
                                    onBookmark = { bookmarkToggle(mod) },
                                    onOpen = {
                                        if (filter == DiscoverFilter.SAVED && !browse.hasApiKey)
                                            offlineSavedId = id
                                        else onOpenRemoteMod(mod.modId, mod.sourceId)
                                    })
                            }
                            if (rows[rowIndex].size == 1 && gridMode) {
                                Spacer(Modifier.weight(1f))
                            }
                        }
                    }
                }
                if (filter != DiscoverFilter.SAVED &&
                    (browse.hasMore || browse.isLoadingMore || browse.loadMoreError != null)) {
                    item {
                        if (browse.loadMoreError != null) {
                            ModsPanel("More results unavailable", "Your existing results are preserved.") {
                                Button(onClick = browseViewModel::loadMore) { Text("Retry more results") }
                            }
                        } else {
                            OutlinedButton(onClick = browseViewModel::loadMore,
                                enabled = !browse.isLoadingMore,
                                modifier = Modifier.fillMaxWidth().testTag("cinderbox.mods.load-more")) {
                                Text(if (browse.isLoadingMore) "Loading…" else "Load more results")
                            }
                        }
                    }
                }
                item {
                    TextButton(onClick = onBrowseMods, modifier = Modifier.fillMaxWidth()) {
                        Text("Browse mod catalog")
                    }
                }
            }
            ModsPane.INSTALLED -> {
                item {
                    ModsSectionHeading("Installed mods", "Detected from your local mod library.")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("Name", "Author", "Status").forEachIndexed { index, label ->
                            ModsSmallChip(label, installedOrder == index) { installedOrder = index }
                        }
                    }
                }
                if (state.isLoading) {
                    item { ModsPanel("Loading installed mods", "Checking local inventory; no files are changed.") }
                } else if (state.error != null) {
                    item { ModsPanel("Mods could not be loaded", "The local mod inventory is unavailable.") }
                } else if (state.installedMods.isEmpty()) {
                    item { ModsPanel("No installed mods found", "Browse without Steam sign-in.") }
                } else {
                    items(installedMods, key = { it.folderName }) { mod ->
                        ModsEntry(title = mod.manifest.name,
                            detail = "${mod.manifest.author.ifBlank { "Unknown author" }} · ${mod.manifest.version}",
                            status = if (mod.enabled) "Enabled" else "Disabled",
                            onClick = { onOpenInstalledMod(mod.manifest.uniqueID) })
                    }
                }
                item {
                    OutlinedButton(onClick = viewModel::loadInstalledMods,
                        modifier = Modifier.fillMaxWidth()) { Text("Refresh installed mods") }
                }
            }
            ModsPane.UPDATES -> {
                item { ModsSectionHeading("Mod updates", "Available update information is advisory, not an install command.") }
                if (state.isCheckingUpdates) {
                    item { ModsPanel("Checking for updates", "The update metadata check is in progress.") }
                }
                if (state.updateError != null) {
                    item { ModsPanel("Update information unavailable", "Cached results may be stale.") }
                }
                if (state.updates.isEmpty()) {
                    item { ModsPanel("No actionable updates listed", "This does not guarantee every mod is current.") }
                } else {
                    items(state.updates.values.sortedBy { it.uniqueID.lowercase(java.util.Locale.ROOT) },
                        key = { it.uniqueID }) { update ->
                        ModsEntry(title = update.uniqueID,
                            detail = "${update.installedVersion} → ${update.latestVersion}",
                            status = "Review in manager", onClick = onOpenAdvancedMods)
                    }
                }
                item {
                    OutlinedButton(onClick = viewModel::checkForUpdates,
                        enabled = !state.isCheckingUpdates && state.installedMods.isNotEmpty(),
                        modifier = Modifier.fillMaxWidth()) { Text("Check update metadata") }
                }
            }
            ModsPane.PROFILES -> {
                item { ModsSectionHeading("Mod profiles", "Saved loadouts are shown without being applied.") }
                if (state.profiles.isEmpty()) {
                    item { ModsPanel("No profiles saved", "Create and review loadouts through advanced management.") }
                } else {
                    items(state.profiles, key = { it.id }) { profile ->
                        ModsEntry(title = profile.name,
                            detail = "${profile.enabledModIds.size} selected mods${if (profile.isProtected) " · Protected" else ""}",
                            status = if (profile.name == state.activeProfileName) "Current" else "Saved",
                            onClick = { onOpenProfileDetail(profile.id) })
                    }
                }
                item {
                    OutlinedButton(onClick = onOpenAdvancedMods,
                        modifier = Modifier.fillMaxWidth()) { Text("Manage profiles") }
                }
            }
        }
    }
}

@Composable
private fun ModsPaneSelector(selected: ModsPane, onSelect: (ModsPane) -> Unit) {
    Row(Modifier.fillMaxWidth().background(Dark.Paper, RoundedCornerShape(14.dp))
        .padding(4.dp).testTag("cinderbox.mods.sections")) {
        ModsPane.entries.forEach { pane ->
            val isSelected = pane == selected
            Surface(color = if (isSelected) Dark.Mint else Dark.Paper,
                contentColor = if (isSelected) Dark.Forest else Dark.Muted,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.weight(1f).heightIn(min = 48.dp)
                    .testTag("cinderbox.mods.section.${pane.name.lowercase(java.util.Locale.ROOT)}")
                    .selectable(selected = isSelected, role = Role.Tab) { onSelect(pane) }) {
                Box(Modifier.fillMaxWidth().heightIn(min = 48.dp).padding(horizontal = 2.dp)
                    .testTag(when (pane) {
                        ModsPane.DISCOVER -> "cinderbox.mods.discover"
                        ModsPane.INSTALLED -> "cinderbox.mods.installed"
                        ModsPane.UPDATES -> "cinderbox.mods.updates"
                        ModsPane.PROFILES -> "cinderbox.mods.profiles"
                    }), contentAlignment = Alignment.Center) {
                    Text(pane.label, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
                }
            }
        }
    }
}

@Composable
private fun ModsSmallChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Surface(color = if (selected) Dark.Mint else Dark.Paper,
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, if (selected) Dark.Forest else Dark.Line),
        modifier = Modifier.heightIn(min = 48.dp).selectable(selected = selected,
            role = Role.Button, onClick = onClick)) {
        Box(Modifier.padding(horizontal = 10.dp, vertical = 8.dp), contentAlignment = Alignment.Center) {
            Text(label, color = if (selected) Dark.Forest else Dark.Ink,
                maxLines = 1, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun ModsChoice(label: String, selected: Boolean, onClick: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
        .selectable(selected = selected, role = Role.RadioButton, onClick = onClick),
        color = if (selected) Dark.Mint else Dark.Paper2, shape = RoundedCornerShape(11.dp)) {
        Box(Modifier.padding(12.dp), contentAlignment = Alignment.CenterStart) {
            Text(label, color = if (selected) Dark.Forest else Dark.Ink)
        }
    }
}

@Composable
private fun RemoteModCard(mod: ModCardData, saved: Boolean, isInstalled: Boolean,
    compact: Boolean, offlineMetadataOnly: Boolean, modifier: Modifier,
    onBookmark: () -> Unit, onOpen: () -> Unit) {
    Surface(modifier = modifier.testTag("nex.r2.card")
            .clickable(role = Role.Button, onClick = onOpen),
        color = Dark.Paper, shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, Dark.Line)) {
        Column {
            Box(Modifier.fillMaxWidth().height(if (compact) 76.dp else 112.dp)
                .background(Dark.Paper3)) {
                // Never fetch provider images for a locally saved offline card.
                if (!offlineMetadataOnly && !mod.pictureUrl.isNullOrBlank()) {
                    AsyncImage(model = mod.pictureUrl, contentDescription = null,
                        modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                } else {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("MOD", color = Dark.Forest, style = MaterialTheme.typography.titleLarge)
                    }
                }
                IconButton(onClick = onBookmark,
                    modifier = Modifier.align(Alignment.TopEnd)
                        .semantics { contentDescription = if (saved) "Remove saved mod" else "Save mod" }) {
                    Text(if (saved) "♥" else "♡", color = Dark.Ink,
                        style = MaterialTheme.typography.titleLarge)
                }
            }
            Column(Modifier.fillMaxWidth().padding(10.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(mod.name, color = Dark.Ink, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                Text("by " + mod.author, color = Dark.Muted, maxLines = 1,
                    overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                if (mod.summary.isNotBlank()) {
                    Text(mod.summary, color = Dark.Muted,
                        maxLines = if (compact) 2 else 3, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodySmall)
                }
                if (!mod.categoryName.isNullOrBlank()) {
                    Text(mod.categoryName, color = Dark.Forest, maxLines = 1,
                        overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall)
                }
                if (mod.version.isNotBlank()) {
                    Text("Version " + mod.version, color = Dark.Muted, maxLines = 1,
                        style = MaterialTheme.typography.labelSmall)
                }
                if (mod.downloads > 0 || mod.endorsements > 0) {
                    Text(listOfNotNull(
                        mod.downloads.takeIf { it > 0 }?.let { NexR2Display.compactCount(it) + " downloads" },
                        mod.endorsements.takeIf { it > 0 }?.let { NexR2Display.compactCount(it) + " endorsements" }
                    ).joinToString(" · "), color = Dark.Muted,
                        style = MaterialTheme.typography.labelSmall, maxLines = 2)
                }
                NexR2Display.dateUtc(mod.lastUpdated)?.let { day ->
                    Text("Updated $day UTC", color = Dark.Muted,
                        style = MaterialTheme.typography.labelSmall)
                }
                Text(if (offlineMetadataOnly) "Saved metadata · Available offline"
                     else if (isInstalled) "Installed locally"
                     else if (saved) "Saved locally · View details"
                     else "View details", color = Dark.Forest,
                    style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun ModsSummary(label: String, count: String, modifier: Modifier = Modifier) {
    Surface(modifier = modifier, color = Dark.Paper, shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, Dark.Line)) {
        Column(Modifier.padding(10.dp)) {
            Text(label, color = Dark.Muted, style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp))
            Spacer(Modifier.height(4.dp))
            Text(count, color = Dark.Ink, style = MaterialTheme.typography.titleMedium)
        }
    }
}

@Composable
private fun ModsSectionHeading(title: String, subtitle: String) {
    Column {
        Text(title, color = Dark.Ink, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
        Text(subtitle, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun ModsPanel(title: String, subtitle: String, content: @Composable () -> Unit = {}) {
    Surface(color = Dark.Paper, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Dark.Line)) {
        Column(Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, color = Dark.Ink, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
            Text(subtitle, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            content()
        }
    }
}

@Composable
private fun ModsEntry(title: String, detail: String, status: String, onClick: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth().clickable(role = Role.Button, onClick = onClick),
        color = Dark.Paper, shape = RoundedCornerShape(17.dp), border = BorderStroke(1.dp, Dark.Line)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, color = Dark.Ink, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
            Text(detail, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            Text(status, color = Dark.Forest, style = MaterialTheme.typography.labelSmall)
        }
    }
}
