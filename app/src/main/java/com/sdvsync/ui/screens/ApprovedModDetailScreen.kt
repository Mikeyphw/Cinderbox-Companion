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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
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
import com.sdvsync.ui.components.BottomTab
import com.sdvsync.ui.components.StardewBottomBar
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.ModDetailViewModel
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale

/** Approved detail route is read-only. Actual downloads remain in legacy guarded details. */
@Composable
fun ApprovedModDetailScreen(
    viewModel: ModDetailViewModel,
    onBack: () -> Unit,
    onReviewFiles: () -> Unit,
    onSelectTab: (BottomTab) -> Unit
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
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
    ApprovedModDetailContent(mod, state.files,
        state.requirements ?: ModRequirementsAssessor.assess(mod, null),
        state.fileListError, saved, onBack, onReviewFiles, onSelectTab) {
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
        if (mod.pictureUrl.isNullOrBlank()) Text("△",fontSize=54.sp,color=Dark.Ink)
        else AsyncImage(model=mod.pictureUrl,contentDescription="Provider image for " + mod.name,
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
    onToggleSaved: () -> Unit
) {
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
                    DetailChip("v" + mod.version,Dark.Muted,Dark.Paper2)
                }
            }
            item {
                Text(mod.description?.takeIf { it.isNotBlank() } ?: mod.summary,
                    color=Dark.Ink,style=MaterialTheme.typography.bodyMedium)
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
                Text("Files & versions",color=Dark.Ink,
                    style=MaterialTheme.typography.titleMedium.copy(fontWeight=FontWeight.Bold))
                Surface(Modifier.fillMaxWidth(),color=Dark.Paper,
                    shape=RoundedCornerShape(18.dp),border=BorderStroke(1.dp,Dark.Line)) {
                    Column(Modifier.padding(15.dp),verticalArrangement=Arrangement.spacedBy(9.dp)) {
                        Text(if(files.isEmpty()) "No file list loaded" else files.size.toString() + " provider files",
                            color=Dark.Ink,style=MaterialTheme.typography.titleSmall)
                        files.take(4).forEach { file ->
                            Text(file.fileName + " · v" + file.fileVersion,color=Dark.Muted,
                                style=MaterialTheme.typography.bodySmall)
                        }
                        if(fileError != null) Text("Provider file list unavailable.",color=Dark.Warn)
                        Text("Actual downloads and file changes require the existing review flow.",
                            color=Dark.Muted,style=MaterialTheme.typography.bodySmall)
                        OutlinedButton(onClick=onReviewFiles,
                            modifier=Modifier.fillMaxWidth().testTag("cinderbox.mod-detail.files")) {
                            Text("Review files & downloads")
                        }
                    }
                }
            }
            item {
                Text("Additional gallery images are not supplied by the current catalog response.",
                    color=Dark.Muted,style=MaterialTheme.typography.bodySmall)
            }
        }
        StardewBottomBar(selectedTab=BottomTab.MODS,onTabSelected=onSelectTab)
    }
}
