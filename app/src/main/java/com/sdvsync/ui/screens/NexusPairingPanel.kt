package com.sdvsync.ui.screens

import android.content.Intent
import org.json.JSONArray
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.sdvsync.mods.NexusPairingBridge
import com.sdvsync.mods.NexusPairingInbox
import com.sdvsync.mods.NexusCompanionPrivacyPolicy
import com.sdvsync.BuildConfig
import com.sdvsync.mods.api.NexusBrowserHandoff
import com.sdvsync.mods.api.NexusBrowserLauncher
import kotlinx.coroutines.delay

/** Explicit opt-in local pairing, deliberately unavailable when the app process is gone. */
@Composable
internal fun NexusPairingPanel() {
    val context = LocalContext.current
    var state by remember { mutableStateOf(NexusPairingBridge.snapshot()) }
    var problem by remember { mutableStateOf(false) }
    var inboxError by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var diagnosticPreview by remember { mutableStateOf<String?>(null) }
    var inbox by remember { mutableStateOf<List<NexusPairingInbox.Entry>>(emptyList()) }
    fun refreshInbox() {
        val loaded = runCatching { NexusPairingInbox.verifiedHistory(context) }
        inboxError = loaded.isFailure
        // Never display a previously cached list if the backing store turns unavailable.
        inbox = loaded.getOrDefault(emptyList())
    }
    LaunchedEffect(Unit) {
        while (true) {
            state = NexusPairingBridge.snapshot()
            refreshInbox()
            delay(1000)
        }
    }
    Column(Modifier.fillMaxWidth().testTag("cbnx03.pairing.panel"),
        verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Firefox companion", style = MaterialTheme.typography.titleMedium)
        Text("Optional read-only queue status and explicit exact-file requests. No Nexus login, tokens or mod installation access is shared.",
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
                if (state.connected) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Column(Modifier.weight(1f)) {
                            Text("Allow exact-file requests from Firefox", style = MaterialTheme.typography.bodyMedium)
                            Text("Off by default. Requests enter a private inbox; opening Nexus still needs your tap.",
                                style = MaterialTheme.typography.bodySmall)
                        }
                        Switch(checked = state.handoffEnabled, onCheckedChange = {
                            NexusPairingBridge.setHandoffEnabled(it)
                            state = NexusPairingBridge.snapshot()
                        }, modifier = Modifier.testTag("cbnx03b.pairing.allow-handoff"))
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { NexusPairingBridge.revoke(); state = NexusPairingBridge.snapshot() },
                        modifier = Modifier.testTag("cbnx03.pairing.revoke")) { Text("Revoke") }
                    OutlinedButton(onClick = { NexusPairingBridge.stop(); state = NexusPairingBridge.snapshot() },
                        modifier = Modifier.testTag("cbnx03.pairing.stop")) { Text("Stop") }
                }
            }
        }
        Text("Exact-file requests", style = MaterialTheme.typography.titleSmall)
        Text("Requests are private and never install or download a mod by themselves. " +
            "Only an explicit tap opens the selected Nexus file.", style = MaterialTheme.typography.bodySmall)
        if (inboxError) Text("Request history unavailable; no new request will be assumed accepted.",
            color = MaterialTheme.colorScheme.error)
        val pending = inbox.filter { it.status == "PENDING" }
        if (pending.isEmpty() && !inboxError) Text("No pending requests.", style = MaterialTheme.typography.bodySmall)
        for (item in pending) {
            Column(Modifier.fillMaxWidth().testTag("cbnx03b.handoff.pending"),
                verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Nexus mod ${item.modId} · exact file ${item.fileId}",
                    style = MaterialTheme.typography.bodyMedium)
                Text("Requested only. No archive downloaded or installed.", style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(enabled = !busy, onClick = {
                        busy = true
                        val opened = runCatching {
                            val url = requireNotNull(NexusBrowserHandoff.createUrl(item.modId, item.fileId))
                            NexusBrowserLauncher.open(context, url)
                            check(NexusPairingInbox.resolve(context, item.id, "OPENED"))
                        }
                        if (opened.isFailure) problem = true
                        refreshInbox()
                        busy = false
                    }, modifier = Modifier.testTag("cbnx03b.handoff.open-exact")) {
                        Text("Open exact Nexus file")
                    }
                    TextButton(enabled = !busy, onClick = {
                        busy = true
                        if (runCatching { NexusPairingInbox.resolve(context, item.id, "DISMISSED") }.isFailure)
                            problem = true
                        refreshInbox()
                        busy = false
                    }, modifier = Modifier.testTag("cbnx03b.handoff.dismiss")) { Text("Dismiss") }
                }
            }
        }
        if (!inboxError) {
            val resolved = inbox.filter { it.status == "OPENED" || it.status == "DISMISSED" }
                .takeLast(8).asReversed()
            Text("Recent handoffs", style = MaterialTheme.typography.titleSmall)
            if (resolved.isEmpty()) Text("No verified recent history.", style = MaterialTheme.typography.bodySmall)
            for (item in resolved) {
                val action = if (item.status == "OPENED") "Opened Nexus page" else "Dismissed"
                Text("$action · mod ${NexusCompanionPrivacyPolicy.redactedId(item.modId)} " +
                    "· file ${NexusCompanionPrivacyPolicy.redactedId(item.fileId)} " +
                    "· ${android.text.format.DateFormat.format("MMM d, HH:mm", item.createdAt)}",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.testTag("cbnx05b.handoff.history"))
            }
            Text("Opened is not downloaded, archived, reviewed or installed.",
                style = MaterialTheme.typography.bodySmall)
        }
        HorizontalDivider()
        Text("Connection and privacy", style = MaterialTheme.typography.titleSmall)
        Text(when {
            !state.listening -> "Pairing is off. Firefox uses its normal browser queue."
            state.connected && state.handoffEnabled -> "Paired · exact-file requests allowed until this window closes."
            state.connected -> "Paired · incoming requests disabled."
            state.code != null -> "Pairing code available locally for a short window."
            else -> "Pairing expired or revoked. Start a new window to reconnect."
        }, style = MaterialTheme.typography.bodySmall)
        Text("Choose Firefox, Cinderbox or another supported manager in the Firefox popup. " +
            "Automatic routing is not enabled by pairing.", style = MaterialTheme.typography.bodySmall)
        Text("Support summary", style = MaterialTheme.typography.titleSmall)
        Text("Preview and explicitly share a small status-only report. " +
            "It contains no Nexus credentials, file identities, browser links or storage paths.",
            style = MaterialTheme.typography.bodySmall)
        OutlinedButton(onClick = {
            val historyResult = runCatching { NexusPairingInbox.verifiedHistory(context) }
            val journalResult = runCatching {
                val prefs = context.getSharedPreferences("cinderbox_mod_download_journal_v1",
                    android.content.Context.MODE_PRIVATE)
                val raw = requireNotNull(prefs.getString("records", null)) { "Journal unavailable" }
                val data = JSONArray(raw)
                check(data.length() <= 60) { "Journal oversized" }
                val identities = mutableSetOf<String>()
                (0 until data.length()).map { index ->
                    val row = data.getJSONObject(index)
                    val id = row.getString("id")
                    check(id.isNotBlank() && id.length <= 64 && identities.add(id)) {
                        "Invalid journal identity"
                    }
                    val status = row.getString("status")
                    check(NexusCompanionPrivacyPolicy.isKnownJobStatus(status)) { "Invalid journal status" }
                    status
                }
            }
            diagnosticPreview = NexusCompanionPrivacyPolicy.report(
                BuildConfig.VERSION_NAME, System.currentTimeMillis(), state.listening,
                state.connected, state.handoffEnabled, historyResult.isSuccess,
                historyResult.getOrNull()?.map { it.status }.orEmpty(), journalResult.isSuccess,
                journalResult.getOrNull().orEmpty())
        }, modifier = Modifier.testTag("cbnx05b.diagnostics.preview")) { Text("Preview support summary") }
        val ready = diagnosticPreview
        if (ready != null) {
            Text(ready, style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.testTag("cbnx05b.diagnostics.redacted"))
            OutlinedButton(onClick = {
                val share = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, ready)
                }
                runCatching { context.startActivity(Intent.createChooser(share, "Share support summary")) }
                    .onFailure { problem = true }
            }, modifier = Modifier.testTag("cbnx05b.diagnostics.share")) {
                Text("Share this summary")
            }
            TextButton(onClick = { diagnosticPreview = null }) { Text("Hide summary") }
        }
        if (problem) Text("Operation unavailable. Check pairing or local request storage.", color = MaterialTheme.colorScheme.error)
        Text("Requires Cinderbox to remain alive for live pairing. Inbox requests survive process restart; regular NXM downloads still work.",
            style = MaterialTheme.typography.bodySmall)
    }
}
