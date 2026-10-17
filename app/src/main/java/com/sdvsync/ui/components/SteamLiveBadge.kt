package com.sdvsync.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.sdvsync.steam.SteamAuthenticator
import com.sdvsync.steam.SteamDiagnostics
import com.sdvsync.ui.theme.SdvSyncThemeExtras
import kotlinx.coroutines.launch

@Composable
fun SteamLiveBadge() {
    val diagnostics by SteamDiagnostics.snapshot.collectAsState()
    val auth: SteamAuthenticator = remember { org.koin.core.context.GlobalContext.get().get() }
    val scope = rememberCoroutineScope()
    var showDetails by remember { mutableStateOf(false) }
    val phase = diagnostics.phase
    val earthy = SdvSyncThemeExtras.isEarthy
    val tones = SdvSyncThemeExtras.colors
    val label = when (phase) {
        SteamDiagnostics.Phase.CONNECTED -> "Steam ✓"
        SteamDiagnostics.Phase.CONNECTING -> "Steam …"
        SteamDiagnostics.Phase.AUTHENTICATING -> "Steam …"
        SteamDiagnostics.Phase.RECONNECTING -> "Steam ↻"
        SteamDiagnostics.Phase.OFFLINE -> "Steam ✕"
    }
    val color = when (phase) {
        SteamDiagnostics.Phase.CONNECTED -> Color(0xFF267D46)
        SteamDiagnostics.Phase.CONNECTING, SteamDiagnostics.Phase.AUTHENTICATING -> Color(0xFF1565C0)
        SteamDiagnostics.Phase.RECONNECTING -> Color(0xFF996000)
        SteamDiagnostics.Phase.OFFLINE -> Color(0xFFA42D30)
    }
    val statusTextColor = if (earthy) when (phase) {
        SteamDiagnostics.Phase.CONNECTED -> tones.synced
        SteamDiagnostics.Phase.CONNECTING, SteamDiagnostics.Phase.AUTHENTICATING -> tones.pullBlue
        SteamDiagnostics.Phase.RECONNECTING -> tones.conflict
        SteamDiagnostics.Phase.OFFLINE -> tones.syncError
    } else color
    Surface(
        color = if (earthy) statusTextColor.copy(alpha = 0.14f) else color,
        shape = RoundedCornerShape(6.dp),
        modifier = Modifier.clickable { showDetails = true }
    ) {
        Text(label, color = if (earthy) statusTextColor else Color.White, style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 6.dp), maxLines = 1)
    }
    if (showDetails) {
        AlertDialog(
            onDismissRequest = { showDetails = false },
            title = { Text("Steam connection") },
            text = { androidx.compose.foundation.layout.Column {
                Text("Status: $label")
                Text("Transport: ${SteamDiagnostics.activeTransport}")
                Text("In current state: ${(System.currentTimeMillis() - diagnostics.sinceMs).coerceAtLeast(0L) / 1000}s")
                Text("Network: ${SteamDiagnostics.networkSummary()}")
                Text("Recent connection failures: ${diagnostics.failures}")
                Text("Connection details are available in hidden Developer diagnostics.")
            } },
            confirmButton = {
                TextButton(onClick = {
                    showDetails = false
                    scope.launch { auth.loginWithSavedSession() }
                }, enabled = phase == SteamDiagnostics.Phase.OFFLINE) { Text("Retry") }
            },
            dismissButton = { TextButton(onClick = { showDetails = false }) { Text("Close") } }
        )
    }
}
