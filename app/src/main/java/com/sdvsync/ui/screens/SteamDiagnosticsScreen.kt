package com.sdvsync.ui.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.sdvsync.steam.SteamDiagnostics
import com.sdvsync.ui.components.StardewTopAppBar
import kotlinx.coroutines.delay

/** Hidden, read-only diagnostics; export uses Storage Access Framework. */
@Composable
fun SteamDiagnosticsScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val snapshot by SteamDiagnostics.snapshot.collectAsState()
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) { while (true) { delay(10_000L); now = System.currentTimeMillis() } }
    val export = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) {
            runCatching { context.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use {
                it.write(SteamDiagnostics.exportJson())
            } }
        }
    }
    Scaffold(topBar = { StardewTopAppBar("Steam diagnostics", navigationIcon = {
        TextButton(onClick = onBack) { Text("Back") }
    }) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp)) {
            Text("Status: ${snapshot.phase}", style = MaterialTheme.typography.titleMedium)
            Text("In current state: ${(now - snapshot.sinceMs).coerceAtLeast(0L) / 1000}s")
            Text("Transport: ${SteamDiagnostics.activeTransport}")
            Text("Android network: ${SteamDiagnostics.networkSummary()}")
            Text("Connection failures: ${snapshot.failures}")
            Spacer(Modifier.height(20.dp))
            Text("Last 60 minutes (each bar = one minute)", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth().height(52.dp), horizontalArrangement = Arrangement.spacedBy(1.dp)) {
                SteamDiagnostics.minuteHistory(now).forEach { phase ->
                    val color = when (phase) {
                        SteamDiagnostics.Phase.CONNECTED -> Color(0xFF267D46)
                        SteamDiagnostics.Phase.CONNECTING, SteamDiagnostics.Phase.AUTHENTICATING -> Color(0xFF1565C0)
                        SteamDiagnostics.Phase.RECONNECTING -> Color(0xFF996000)
                        SteamDiagnostics.Phase.OFFLINE -> Color(0xFFA42D30)
                        null -> Color.LightGray
                    }
                    Box(Modifier.weight(1f).fillMaxHeight().background(color))
                }
            }
            Spacer(Modifier.height(6.dp))
            Text("Green: online  •  Blue: connecting  •  Amber: retry  •  Red: offline  •  Gray: no data",
                style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(20.dp))
            Button(onClick = { export.launch("cinderbox-steam-diagnostics.json") }) { Text("Export sanitized JSON") }
            Text("Event timestamps and network capability booleans only; no credentials, device IDs, URLs, tokens or SSIDs.",
                style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(16.dp))
            snapshot.events.asReversed().take(90).forEach { event ->
                val date = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.ROOT).format(java.util.Date(event.timeMs))
                Text("$date  ${event.phase}: ${event.message}", style = MaterialTheme.typography.bodySmall)
                HorizontalDivider()
            }
        }
    }
}
