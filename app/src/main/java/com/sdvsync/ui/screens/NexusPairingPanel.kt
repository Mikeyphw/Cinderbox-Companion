package com.sdvsync.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.sdvsync.mods.NexusPairingBridge
import kotlinx.coroutines.delay

/** Explicit opt-in local pairing, deliberately unavailable when the app process is gone. */
@Composable
internal fun NexusPairingPanel() {
    val context = LocalContext.current
    var state by remember { mutableStateOf(NexusPairingBridge.snapshot()) }
    var problem by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        while (true) {
            state = NexusPairingBridge.snapshot()
            delay(1000)
        }
    }
    Column(Modifier.fillMaxWidth().testTag("cbnx03.pairing.panel"),
        verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Firefox companion", style = MaterialTheme.typography.titleMedium)
        Text("Optional read-only queue status. No Nexus login, tokens or mod installation access is shared.",
            style = MaterialTheme.typography.bodySmall)
        when {
            !state.listening -> {
                Text("Not connected", style = MaterialTheme.typography.bodyMedium)
                Button(onClick = {
                    problem = false
                    state = runCatching { NexusPairingBridge.start(context) }.getOrElse {
                        problem = true
                        NexusPairingBridge.snapshot()
                    }
                }, modifier = Modifier.testTag("cbnx03.pairing.start")) {
                    Text("Start pairing window")
                }
            }
            else -> {
                Text("Local-only pairing window · ${state.remainingSeconds}s remaining",
                    style = MaterialTheme.typography.bodySmall)
                if (state.code != null) {
                    Text("Pairing code: ${state.code}", style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.testTag("cbnx03.pairing.code"))
                    Text("Enter this code in the Stardew Nexus Queue Firefox popup.",
                        style = MaterialTheme.typography.bodySmall)
                } else {
                    Text(if (state.connected) "Paired for read-only status" else "Pairing code expired or revoked",
                        style = MaterialTheme.typography.bodyMedium)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { NexusPairingBridge.revoke(); state = NexusPairingBridge.snapshot() },
                        modifier = Modifier.testTag("cbnx03.pairing.revoke")) { Text("Revoke") }
                    OutlinedButton(onClick = { NexusPairingBridge.stop(); state = NexusPairingBridge.snapshot() },
                        modifier = Modifier.testTag("cbnx03.pairing.stop")) { Text("Stop") }
                }
            }
        }
        if (problem) Text("Could not start the local pairing window.", color = MaterialTheme.colorScheme.error)
        Text("Requires Cinderbox to remain alive. If unavailable, regular NXM downloads still work.",
            style = MaterialTheme.typography.bodySmall)
    }
}
