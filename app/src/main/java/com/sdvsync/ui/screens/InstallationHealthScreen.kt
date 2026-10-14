package com.sdvsync.ui.screens

import android.content.pm.PackageManager
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.sdvsync.local.InstallAssessment
import com.sdvsync.local.InstallHealth
import com.sdvsync.local.InstallationScanner
import com.sdvsync.local.InstallationSnapshot
import com.sdvsync.ui.components.StardewTopAppBar
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/** Local-first, read-only status. Never moves/replaces game, saves or SMAPI data. */
@Composable
fun InstallationHealthScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val prefs = remember(context) { context.getSharedPreferences("m4_local_install", android.content.Context.MODE_PRIVATE) }
    var selectedPath by remember { mutableStateOf(prefs.getString("game_dir", null) ?: "/storage/emulated/0/Download/StardewValley") }
    var refresh by remember { mutableIntStateOf(0) }
    var report by remember { mutableStateOf<InstallationSnapshot?>(null) }
    LaunchedEffect(selectedPath, refresh) {
        report = withContext(Dispatchers.IO) {
            @Suppress("DEPRECATION")
            val installed = try { context.packageManager.getPackageInfo("com.game.cinderbox", 0); true }
            catch (_: PackageManager.NameNotFoundException) { false }
            InstallationScanner.scan(File(selectedPath), installed)
        }
    }
    Scaffold(topBar = { StardewTopAppBar("Installation health", navigationIcon = {
        TextButton(onClick = onBack) { Text("Back") }
    }) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp)) {
            Text("Read-only checks. Detection is not cryptographic integrity verification.", style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(value = selectedPath, onValueChange = {
                selectedPath = it
                prefs.edit().putString("game_dir", it).apply()
            }, label = { Text("Selected game folder") }, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(8.dp))
            Button(onClick = { refresh++ }) { Text("Rescan installations") }
            Spacer(Modifier.height(16.dp))
            report?.let { result ->
                HealthRow("Selected game directory", result.selectedGame)
                HealthRow("Cinderbox GameFiles", result.cinderboxGame)
                HealthRow("SMAPI", result.smapi)
                HealthRow("Cinderbox app", result.cinderboxApp)
                Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(12.dp)) {
                        Text("Destination storage: ${if (result.storage.writable) "Writable" else "Blocked"}",
                            style = MaterialTheme.typography.titleSmall)
                        Text(result.storage.details, style = MaterialTheme.typography.bodySmall)
                    }
                }
            } ?: CircularProgressIndicator()
            Spacer(Modifier.height(10.dp))
            Text("Missing, inaccessible and incomplete are different states. Cinderbox will not overwrite an existing game automatically.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun HealthRow(title: String, result: InstallAssessment) {
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(Modifier.padding(12.dp)) {
            Text("$title: ${result.health.name.replace('_', ' ')}", style = MaterialTheme.typography.titleSmall)
            Text(result.details, style = MaterialTheme.typography.bodySmall)
            Text(result.location, style = MaterialTheme.typography.labelSmall)
        }
    }
}
