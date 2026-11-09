package com.sdvsync.ui.screens

import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.sdvsync.mods.ModRequirementsAssessor
import com.sdvsync.mods.ModRequirementsReport
import com.sdvsync.mods.RequirementVerdict
import com.sdvsync.mods.models.RemoteMod
import com.sdvsync.mods.models.RemoteModFile
import com.sdvsync.mods.models.ModDownloadProgress
import com.sdvsync.mods.models.ModDownloadState
import com.sdvsync.mods.ModDownloadPreferences
import com.sdvsync.mods.api.NexusModPageLinks
import com.sdvsync.mods.api.NexusBrowserHandoff
import com.sdvsync.mods.api.NexusBrowserLauncher
import com.sdvsync.ui.components.HtmlText
import com.sdvsync.ui.components.toHtmlIfFormatted
import com.sdvsync.mods.api.NexR2Display
import com.sdvsync.ui.components.BottomTab
import com.sdvsync.ui.components.StardewBottomBar
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.ModDetailViewModel
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale

/** Unified native details; downloads use the unchanged mandatory review queue. */
@Composable
fun ApprovedModDetailScreen(
    viewModel: ModDetailViewModel,
    onBack: () -> Unit,
    onReviewFiles: () -> Unit,
    onSelectTab: (BottomTab) -> Unit,
    requestedFileId: String? = null
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    val prefs = remember(context) {
        context.getSharedPreferences("ux05_mod_bookmarks", Context.MODE_PRIVATE)
    }
    val mod = state.mod
    var saved by remember { mutableStateOf(false) }
    LaunchedEffect(mod?.modId, mod?.sourceId) {
        val key = mod?.let { (it.sourceId + ":" + it.modId).lowercase(Locale.ROOT) }
        val items = runCatching { JSONArray(prefs.getString("cards", "[]")) }.getOrDefault(JSONArray())
        saved = key != null && (0 until items.length()).any { index ->
            val item = items.optJSONObject(index)
            item != null && (item.optString("source") + ":" + item.optString("id"))
                .lowercase(Locale.ROOT) == key
        }
    }
    if (mod == null) {
        Column(Modifier.fillMaxSize().background(Dark.Background).padding(20.dp)) {
            Text(if (state.isLoading) "Loading mod details" else "Mod details unavailable", color=Dark.Ink)
            if (state.error != null) Text("Provider details could not be loaded.", color=Dark.Warn)
            TextButton(onClick=onBack) { Text("Back") }
        }
        return
    }
    val onToggleSaved = {
        val key = (mod.sourceId + ":" + mod.modId).lowercase(Locale.ROOT)
        val old = runCatching { JSONArray(prefs.getString("cards", "[]")) }.getOrDefault(JSONArray())
        val next = JSONArray()
        for (i in 0 until old.length()) {
            val item = old.optJSONObject(i) ?: continue
            if ((item.optString("source") + ":" + item.optString("id"))
                .lowercase(Locale.ROOT) != key && next.length() < 255) next.put(item)
        }
        if (!saved) next.put(JSONObject().put("source", mod.sourceId.take(40))
            .put("id", mod.modId.take(80)).put("name", mod.name.take(120))
            .put("author", mod.author.take(80)).put("version", mod.version.take(32))
            .put("category", mod.categoryName.orEmpty().take(60))
            .put("picture", mod.pictureUrl.orEmpty().take(500)))
        if (prefs.edit().putString("cards", next.toString()).commit()) saved = !saved
    }
    ApprovedModDetailContent(
        mod, state.files, state.requirements ?: ModRequirementsAssessor.assess(mod, null),
        state.fileListError, saved, onBack, onReviewFiles, onSelectTab, onToggleSaved,
        onDownloadForReview = viewModel::installFile,
        downloadProgress = state.downloadProgress,
        requestInFlight = state.isDownloading,
        downloadError = state.error,
        downloadErrorUrl = state.downloadErrorUrl,
        onOpenExternal = { url -> uriHandler.openUri(url) },
        onBrowserHandoff = { url -> NexusBrowserLauncher.open(context, url) },
        requestedFileId = requestedFileId
    )
}

private fun displayDownloads(count: Int): String = when {
    count >= 1_000_000 -> "%.1fM".format(Locale.US, count / 1_000_000.0)
    count >= 1_000 -> "%.1fK".format(Locale.US, count / 1_000.0)
    else -> count.toString()
}

@Composable
private fun DetailChip(label: String, textColor: Color, background: Color) {
    Surface(color=background, shape=RoundedCornerShape(50)) {
        Text(label, color=textColor, style=MaterialTheme.typography.labelSmall,
            modifier=Modifier.padding(horizontal=9.dp,vertical=6.dp))
    }
}

@Composable
private fun ModDetailCover(mod: RemoteMod) {
    Box(Modifier.fillMaxWidth().height(142.dp).clip(RoundedCornerShape(20.dp))
        .background(Brush.linearGradient(listOf(Color(0xFF6D9E76),Color(0xFF285C51))))
        .testTag("cinderbox.mod-detail.cover"), contentAlignment=Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val landscape=Path().apply {
                moveTo(0f,size.height)
                lineTo(size.width*.35f,size.height*.7f)
                lineTo(size.width*.76f,size.height*.4f)
                lineTo(size.width,size.height*.47f)
                lineTo(size.width,size.height)
                close()
            }
            drawPath(landscape,Color(0xFF548678))
        }
        val providerImage = NexR2Display.imageUrl(mod.pictureUrl)
        if (providerImage == null) Text("△",fontSize=54.sp,color=Dark.Ink)
        else AsyncImage(model=providerImage,contentDescription="Provider image for " + mod.name,
            modifier=Modifier.fillMaxSize())
    }
}

@Composable
fun ApprovedModDetailContent(
    mod: RemoteMod,
    files: List<RemoteModFile>,
    requirements: ModRequirementsReport,
    fileError: String?,
    saved: Boolean,
    onBack: () -> Unit,
    onReviewFiles: () -> Unit,
    onSelectTab: (BottomTab) -> Unit,
    onToggleSaved: () -> Unit,
    onDownloadForReview: (String) -> Unit = {},
    downloadProgress: ModDownloadProgress = ModDownloadProgress(),
    requestInFlight: Boolean = false,
    downloadError: String? = null,
    downloadErrorUrl: String? = null,
    onOpenExternal: (String) -> Unit = {},
    onBrowserHandoff: (String) -> Unit = {},
    requestedFileId: String? = null
) {
    var fileIdQuery by rememberSaveable(mod.modId, requestedFileId) {
        mutableStateOf(requestedFileId.orEmpty())
    }
    val exactMatches = files.filter { it.fileId == requestedFileId }
    val selectedFile = exactMatches.singleOrNull()
    val visibleFiles = if (fileIdQuery.isBlank()) files
        else files.filter { it.fileId == fileIdQuery.trim() }
    // Different Nexus file IDs may be queued while another archive downloads.
    val downloadBusy = requestInFlight
    Column(Modifier.fillMaxSize().background(Dark.Background).testTag("cinderbox.screen.mod-detail")) {
        Row(Modifier.fillMaxWidth().height(57.dp).padding(horizontal=20.dp),
            verticalAlignment=Alignment.CenterVertically) {
            Surface(color=Dark.Mint,shape=RoundedCornerShape(12.dp)) {
                Text("✿",color=Dark.Forest,modifier=Modifier.padding(11.dp))
            }
            Spacer(Modifier.width(10.dp))
            Column {
                Text("Cinderbox",color=Dark.Ink,style=MaterialTheme.typography.titleSmall)
                Text("MOD LIBRARY",color=Dark.Muted,style=MaterialTheme.typography.labelSmall)
            }
        }
        LazyColumn(Modifier.weight(1f).testTag("cinderbox.mod-detail.list"),contentPadding=PaddingValues(
            start=18.dp,end=18.dp,top=8.dp,bottom=24.dp),
            verticalArrangement=Arrangement.spacedBy(13.dp)) {
            item {
                Row(verticalAlignment=Alignment.CenterVertically) {
                    TextButton(onClick=onBack,modifier=Modifier.testTag("cinderbox.mod-detail.back")) {
                        Text("‹",color=Dark.Ink,fontSize=27.sp)
                    }
                    Column {
                        Text("Mod details",color=Dark.Ink,
                            style=MaterialTheme.typography.headlineSmall.copy(fontWeight=FontWeight.Bold),
                            modifier=Modifier.semantics { heading() })
                        Text("Browse / " + (mod.categoryName ?: "Mods"),color=Dark.Muted,
                            style=MaterialTheme.typography.bodySmall)
                    }
                }
            }
            // Exact-ID lookup is immediately visible, not buried in a long file list.
            if (requestedFileId != null) {
                item {
                    Surface(Modifier.fillMaxWidth().testTag("cbnx01.id-lookup.result"),
                        color = Dark.Paper, shape = RoundedCornerShape(18.dp),
                        border = BorderStroke(1.dp, Dark.Line)) {
                        Column(Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Requested Nexus file #$requestedFileId", color = Dark.Ink,
                                style = MaterialTheme.typography.titleMedium)
                            if (selectedFile == null) {
                                Text("This exact file is not in the loaded provider list (or is still loading). " +
                                    "No different file will be selected.",
                                    color = Dark.Warn, style = MaterialTheme.typography.bodySmall)
                                if (fileError != null) Text("Nexus file list unavailable.", color = Dark.Warn)
                            } else {
                                Text(NexR2Display.text(selectedFile.fileName, 120), color = Dark.Ink)
                                Text("Verified in the current provider file list · ID ${selectedFile.fileId}",
                                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                                OutlinedButton(onClick = { onDownloadForReview(selectedFile.fileId) },
                                    enabled = !downloadBusy, modifier = Modifier.fillMaxWidth()
                                        .testTag("cbnx01.id-lookup.download")) {
                                    Text(if (ModDownloadPreferences.requiresApproval(context)) "Download exact file for review" else "Download exact file")
                                }
                                NexusBrowserHandoff.createUrl(mod.modId, selectedFile.fileId)?.let { url ->
                                    OutlinedButton(onClick = { onBrowserHandoff(url) },
                                        modifier = Modifier.fillMaxWidth()
                                            .testTag("cbnx01.id-lookup.browser")) {
                                        Text("Open exact file in Iceraven")
                                    }
                                }
                            }
                        }
                    }
                }
            }
            item { ModDetailCover(mod) }
            item {
                Row(verticalAlignment=Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(mod.name,color=Dark.Ink,
                            style=MaterialTheme.typography.headlineSmall.copy(fontWeight=FontWeight.Bold))
                        Text("by " + mod.author,color=Dark.Muted,style=MaterialTheme.typography.bodySmall)
                    }
                    IconButton(onClick=onToggleSaved,modifier=Modifier.testTag("cinderbox.mod-detail.saved")) {
                        Text(if(saved) "♥" else "♡",fontSize=25.sp,color=Dark.Ink)
                    }
                }
            }
            item {
                Row(horizontalArrangement=Arrangement.spacedBy(7.dp)) {
                    if(requirements.installedSourceMatched)
                        DetailChip("Installed",Dark.Forest,Dark.Mint)
                    DetailChip(when(requirements.overall) {
                        RequirementVerdict.BLOCKED -> "Blocked"
                        RequirementVerdict.REVIEW -> "Review needed"
                        RequirementVerdict.UNKNOWN -> "Not verified"
                        RequirementVerdict.CHECKED -> "Checks complete"
                    },Dark.Warn,Dark.WarnBackground)
                    if (mod.version.isNotBlank()) DetailChip("v" + NexR2Display.text(mod.version, 40),
                        Dark.Muted,Dark.Paper2)
                }
            }
            item {
                Text("Provider description", color = Dark.Muted, style = MaterialTheme.typography.labelMedium)
                val description = mod.description?.takeIf { it.isNotBlank() } ?: mod.summary
                if (description.isBlank()) {
                    Text("Provider description unavailable.", color = Dark.Muted,
                        style = MaterialTheme.typography.bodyMedium)
                } else {
                    RichNexusDescription(description, Modifier.testTag("nex.r2.detail.description"))
                }
            }
            item {
                Text("At a glance",color=Dark.Ink,
                    style=MaterialTheme.typography.titleMedium.copy(fontWeight=FontWeight.Bold))
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                    Surface(Modifier.weight(1f),color=Dark.Paper,
                        shape=RoundedCornerShape(18.dp),border=BorderStroke(1.dp,Dark.Line)) {
                        Column(Modifier.padding(14.dp)) {
                            Text("DOWNLOADS",color=Dark.Muted,style=MaterialTheme.typography.labelSmall)
                            Text(displayDownloads(mod.downloads),color=Dark.Ink,style=MaterialTheme.typography.titleLarge)
                            Text("Provider-reported",color=Dark.Muted,style=MaterialTheme.typography.bodySmall)
                        }
                    }
                    Surface(Modifier.weight(1f),color=Dark.Paper,
                        shape=RoundedCornerShape(18.dp),border=BorderStroke(1.dp,Dark.Line)) {
                        Column(Modifier.padding(14.dp)) {
                            Text("CATEGORY",color=Dark.Muted,style=MaterialTheme.typography.labelSmall)
                            Text(mod.categoryName ?: "Unspecified",color=Dark.Ink,
                                style=MaterialTheme.typography.titleMedium)
                            Text("Provider category",color=Dark.Muted,style=MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                if (mod.endorsements > 0) {
                    Spacer(Modifier.height(7.dp))
                    Text(NexR2Display.compactCount(mod.endorsements) + " provider endorsements",
                        color=Dark.Muted, style=MaterialTheme.typography.bodySmall)
                }
                NexR2Display.dateUtc(mod.lastUpdated)?.let { day ->
                    Text("Provider updated $day UTC", color=Dark.Muted,
                        style=MaterialTheme.typography.bodySmall)
                }
            }
            item {
                Text("Compatibility",color=Dark.Ink,
                    style=MaterialTheme.typography.titleMedium.copy(fontWeight=FontWeight.Bold))
            }
            item {
                Surface(Modifier.fillMaxWidth().testTag("cinderbox.mod-detail.compatibility"),
                    color=Dark.Paper,shape=RoundedCornerShape(18.dp),border=BorderStroke(1.dp,Dark.Line)) {
                    Column(Modifier.padding(15.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                        Text(when(requirements.overall) {
                            RequirementVerdict.BLOCKED -> "Blocked by local requirements"
                            RequirementVerdict.REVIEW -> "Review needed"
                            else -> "Compatibility not verified"
                        },color=Dark.Ink,style=MaterialTheme.typography.titleSmall)
                        Text("Evidence is scoped to local manifests. Game, loader and Android runtime support are not verified.",
                            color=Dark.Muted,style=MaterialTheme.typography.bodySmall)
                        requirements.findings.forEach { finding ->
                            HorizontalDivider(color=Dark.Line)
                            Text(finding.title,color=Dark.Ink,
                                style=MaterialTheme.typography.bodySmall.copy(fontWeight=FontWeight.Bold))
                            Text(finding.expected + " · " + finding.observed,color=Dark.Muted,
                                style=MaterialTheme.typography.bodySmall)
                            Text(finding.explanation + " · Source: " + finding.source,
                                color=Dark.Muted,style=MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
            item {
                Text("Files & versions", color = Dark.Ink,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
                Surface(Modifier.fillMaxWidth(), color = Dark.Paper,
                    shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Dark.Line)) {
                    Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        Text(if (files.isEmpty()) "No file list loaded" else "${files.size} provider files",
                            color = Dark.Ink, style = MaterialTheme.typography.titleSmall)
                        OutlinedTextField(value = fileIdQuery,
                            onValueChange = { fileIdQuery = it.take(24) },
                            label = { Text("Find exact file ID") }, singleLine = true,
                            modifier = Modifier.fillMaxWidth().testTag("cbnx01.detail.file-id-filter"))
                        if (fileIdQuery.isNotBlank() && visibleFiles.isEmpty()) {
                            Text("No provider file matches ID ${fileIdQuery.trim()}. " +
                                "Other files are hidden, not substituted.",
                                color = Dark.Warn, style = MaterialTheme.typography.bodySmall)
                        }
                        // Only the current link-resolution gesture is single-flight.
                        val busy = requestInFlight
                        // Preserve the original grouping for unfiltered browsing;
                        // group only the exact filtered provider data when requested.
                        // Both paths retain the provider-side 120-file bound.
                        val displayedGroups = if (fileIdQuery.isBlank())
                            NexR2Display.groupedFiles(files)
                        else NexR2Display.groupedFiles(visibleFiles)
                        displayedGroups.forEach { group ->
                            HorizontalDivider(color = Dark.Line)
                            Text(group.kind.title, color = Dark.Ink,
                                style = MaterialTheme.typography.titleSmall,
                                modifier = Modifier.testTag("nex.r2.files.group"))
                            group.files.forEach { file ->
                                var expanded by remember(file.fileId) { mutableStateOf(false) }
                                Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                    Text(NexR2Display.text(file.fileName, 120),
                                        color = Dark.Ink, style = MaterialTheme.typography.bodyMedium)
                                    Text("File ID: ${file.fileId}", color = Dark.Muted,
                                        style = MaterialTheme.typography.labelSmall)
                                    Text(listOfNotNull(
                                        NexR2Display.text(file.fileVersion, 35).takeIf { it.isNotBlank() }
                                            ?.let { "v$it" },
                                        NexR2Display.fileSize(file.fileSize),
                                        NexR2Display.dateUtc(file.uploadedAt)?.let { "$it UTC" }
                                    ).joinToString(" · "), color = Dark.Muted,
                                        style = MaterialTheme.typography.labelSmall)
                                    val hasNotes = file.description.isNotBlank() || !file.changelogHtml.isNullOrBlank()
                                    if (hasNotes) {
                                        TextButton(onClick = { expanded = !expanded }) {
                                            Text(if (expanded) "Hide file notes" else "Read file notes",
                                                color = Dark.Forest)
                                        }
                                        if (expanded) {
                                            if (file.description.isNotBlank())
                                                RichNexusDescription(file.description.take(20_000))
                                            file.changelogHtml?.takeIf { it.isNotBlank() }?.let {
                                                Text("Changelog", color = Dark.Ink,
                                                    style = MaterialTheme.typography.labelSmall)
                                                RichNexusDescription(it.take(20_000))
                                            }
                                        }
                                    }
                                    OutlinedButton(
                                        onClick = { onDownloadForReview(file.fileId) },
                                        enabled = !busy,
                                        modifier = Modifier.fillMaxWidth()
                                            .testTag("nex.r5.download-for-review")
                                    ) { Text(if (ModDownloadPreferences.requiresApproval(context)) "Download for review" else "Download and install") }
                                    // Explicit browser-assisted path preserves the selected file ID.
                                    NexusBrowserHandoff.createUrl(mod.modId, file.fileId)?.let { handoff ->
                                        OutlinedButton(
                                            onClick = { onBrowserHandoff(handoff) },
                                            modifier = Modifier.fillMaxWidth()
                                                .testTag("cbnx01.browser-handoff")
                                        ) { Text("Browser + NXM") }
                                    }
                                    HorizontalDivider(color = Dark.Line)
                                }
                            }
                        }
                        if (fileError != null)
                            Text("Provider file list unavailable.", color = Dark.Warn)
                        when (downloadProgress.state) {
                            ModDownloadState.DOWNLOADING -> Text("Downloading archive…", color = Dark.Ink)
                            ModDownloadState.REVIEW_REQUIRED -> Text(
                                "Downloaded. Open Mods to review and approve file changes.",
                                color = Dark.Forest, modifier = Modifier.testTag("nex.r5.review-required"))
                            ModDownloadState.ERROR -> Text(
                                downloadProgress.errorMessage ?: "Download failed.", color = Dark.Warn)
                            else -> Unit
                        }
                        if (downloadError != null)
                            Text(downloadError, color = Dark.Warn, style = MaterialTheme.typography.bodySmall)
                        downloadErrorUrl?.let { fallback ->
                            if (NexusModPageLinks.safeExternalHttps(fallback) != null)
                                OutlinedButton(onClick = { onBrowserHandoff(fallback) },
                                    modifier = Modifier.fillMaxWidth()) { Text("Open selected file in Iceraven") }
                        }
                        Text(if (ModDownloadPreferences.requiresApproval(context)) "A download is staged for mandatory review; it never silently installs." else "Validated downloads install automatically. Unsafe archives remain for review.",
                            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                        OutlinedButton(onClick = onReviewFiles,
                            modifier = Modifier.fillMaxWidth().testTag("cinderbox.mod-detail.files")) {
                            Text("More file download options")
                        }
                    }
                }
            }
            item {
                Text("Media", color = Dark.Ink,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.testTag("nex.r5.media"))
                Text("The cover is the only image returned by the verified mod-details response. " +
                    "Additional images and videos open on Nexus; no media is invented.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                NexusModPageLinks.forTab(mod.modId, "images")?.let { url ->
                    OutlinedButton(onClick = { onOpenExternal(url) },
                        modifier = Modifier.fillMaxWidth().testTag("nex.r5.images")) {
                        Text("View images on Nexus")
                    }
                }
                NexusModPageLinks.forTab(mod.modId, "videos")?.let { url ->
                    TextButton(onClick = { onOpenExternal(url) },
                        modifier = Modifier.fillMaxWidth().testTag("nex.r5.videos")) {
                        Text("View videos on Nexus")
                    }
                }
            }
            item {
                Text("Posts", color = Dark.Ink,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.testTag("nex.r5.posts"))
                Text("Mod-specific Posts are not exposed by a verified API contract. " +
                    "Read comments and replies on Nexus in your browser.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                NexusModPageLinks.forTab(mod.modId, "posts")?.let { url ->
                    OutlinedButton(onClick = { onOpenExternal(url) },
                        modifier = Modifier.fillMaxWidth().testTag("nex.r5.open-posts")) {
                        Text("Read posts on Nexus")
                    }
                }
            }
        }
        StardewBottomBar(selectedTab=BottomTab.MODS,onTabSelected=onSelectTab)
    }
}

/** Read-only formatted provider text; URL spans are filtered to safe HTTPS destinations. */
@Composable
private fun RichNexusDescription(raw: String, modifier: Modifier = Modifier) {
    val bounded = raw.take(32_000)
    val formatted = remember(bounded) { toHtmlIfFormatted(bounded) }
    if (formatted == null) {
        Text(bounded, color = Dark.Ink, style = MaterialTheme.typography.bodyMedium,
            modifier = modifier)
    } else {
        HtmlText(html = formatted, textColor = Dark.Ink.toArgb(),
            linkColor = Dark.Forest.toArgb(),
            textSizeSp = MaterialTheme.typography.bodyMedium.fontSize.value,
            modifier = modifier)
    }
}
