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
import com.sdvsync.mods.NexusLab03CPolicy
import com.sdvsync.mods.NexusLab03Evidence
import com.sdvsync.mods.NexusLab03DArchiveStage
import com.sdvsync.mods.NexusLab04SyntheticTransaction
import com.sdvsync.mods.NexusCompanionPrivacyPolicy
import com.sdvsync.BuildConfig
import com.sdvsync.mods.api.NexusBrowserHandoff
import com.sdvsync.mods.api.NexusBrowserLauncher
import kotlinx.coroutines.delay
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Explicit opt-in local pairing, deliberately unavailable when the app process is gone. */
@Composable
internal fun NexusPairingPanel() {
    val context = LocalContext.current
    var state by remember { mutableStateOf(NexusPairingBridge.snapshot()) }
    var problem by remember { mutableStateOf(false) }
    var inboxError by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var lab03Outcome by remember { mutableStateOf<String?>(null) }
    var lab03dOutcome by remember { mutableStateOf<String?>(null) }
    var lab04Outcome by remember { mutableStateOf<String?>(null) }
    var lab04Action by remember { mutableStateOf<String?>(null) }
    var lab03cSelection by remember { mutableStateOf<NexusPairingInbox.Entry?>(null) }
    var lab03cFeedback by remember { mutableStateOf<String?>(null) }
    val lab03Scope = rememberCoroutineScope()
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
        Text(if (BuildConfig.CBNX_LAB) "Firefox companion · ISOLATED LAB (127.0.0.1:38472)" else "Firefox companion",
            style = MaterialTheme.typography.titleMedium)
        Text("Optional read-only queue status and explicit exact-file requests. No Nexus login, tokens or mod installation access is shared.",
            style = MaterialTheme.typography.bodySmall)
        if (BuildConfig.CBNX_LAB) {
            Text(when {
                state.connected && state.handoffEnabled -> "LAB paired · exact-file requests allowed."
                state.connected -> "LAB paired · enable exact-file requests below."
                state.listening && state.code != null -> "LAB awaiting Iceraven pairing · enter the code in the LAB extension."
                state.listening -> "LAB waiting · pairing code expired or revoked."
                else -> "LAB disconnected · start a pairing window."
            }, modifier = Modifier.testTag("cbnx06.lab.pairing-status"),
                style = MaterialTheme.typography.bodyMedium)
        }
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
                    Text(if (BuildConfig.CBNX_LAB) "Enter this code in the LAB02C Firefox popup (port 38472)." else "Enter this code in the Stardew Nexus Queue Firefox popup.",
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
        // LAB: always show consent, but never enable it before a real local pairing.
        // Production preserves its historical visibility (connected only).
        if (BuildConfig.CBNX_LAB || state.connected) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Column(Modifier.weight(1f)) {
                    Text("Allow exact-file requests from Firefox", style = MaterialTheme.typography.bodyMedium)
                    Text(if (state.connected)
                            "Off by default. Requests enter a private inbox; opening Nexus still needs your tap."
                         else "Disabled until paired. Enter the code in the isolated Iceraven extension first.",
                        style = MaterialTheme.typography.bodySmall)
                }
                Switch(checked = state.connected && state.handoffEnabled,
                    enabled = state.connected && state.listening,
                    onCheckedChange = {
                        if (state.connected && state.listening) {
                            problem = false
                            runCatching { NexusPairingBridge.setHandoffEnabled(it) }
                                .onFailure { problem = true }
                            state = NexusPairingBridge.snapshot()
                        }
                    }, modifier = Modifier.testTag("cbnx03b.pairing.allow-handoff"))
            }
        }
        if (BuildConfig.CBNX_LAB) {
            Text("LAB03A synthetic only · Not downloaded from Nexus", style = MaterialTheme.typography.titleSmall)
            Text("Generate a deterministic test ZIP and preview it using Cinderbox's real archive reviewer. No installation or live Nexus traffic.",
                style = MaterialTheme.typography.bodySmall)
            OutlinedButton(enabled = !busy, onClick = {
                busy = true
                lab03Scope.launch {
                    val result = withContext(Dispatchers.IO) {
                        runCatching { NexusLab03Evidence.previewSynthetic(context) }
                    }
                    lab03Outcome = result.fold(
                        onSuccess = { "LAB03A SYNTHETIC PREVIEW: ${it.proposedChanges} proposed change · SHA-256 ${it.archiveSha256.take(16)}… · no install" },
                        onFailure = { "LAB03A REFUSED: ${it.javaClass.simpleName}" }
                    )
                    busy = false
                }
            }, modifier = Modifier.testTag("cbnx06.lab03a.preview-synthetic")) {
                Text("Preview synthetic ZIP (LAB only)")
            }
            lab03Outcome?.let { Text(it, modifier = Modifier.testTag("cbnx06.lab03a.result"),
                style = MaterialTheme.typography.bodySmall) }
            Text("LAB03D · Private synthetic archive evidence", style = MaterialTheme.typography.titleSmall)
            Text("Stage the LAB-generated ZIP under this app's private data directory, compare SHA-256 and size, " +
                "and verify the synthetic-only source receipt. This does not verify Nexus provenance, download or install anything.",
                style = MaterialTheme.typography.bodySmall)
            OutlinedButton(enabled = !busy, onClick = {
                busy = true
                lab03Scope.launch {
                    val result = withContext(Dispatchers.IO) {
                        runCatching { NexusLab03DArchiveStage.stageSynthetic(context) }
                    }
                    lab03dOutcome = result.fold(
                        onSuccess = { "LAB03D LOCAL SYNTHETIC ARCHIVE VERIFIED · SHA-256 ${it.sha256.take(16)}… " +
                            "· ${it.archiveBytes} bytes · ${it.provenance} · Nexus provenance NOT VERIFIED · no install" },
                        onFailure = { "LAB03D REFUSED: ${it.javaClass.simpleName} · no install" }
                    )
                    busy = false
                }
            }, modifier = Modifier.testTag("cbnx06.lab03d.stage-synthetic")) {
                Text("Stage and verify synthetic archive (LAB only)")
            }
            lab03dOutcome?.let {
                Text(it, modifier = Modifier.testTag("cbnx06.lab03d.stage-feedback"),
                    style = MaterialTheme.typography.bodySmall)
            }
            Text("LAB04 · Synthetic installation and rollback", style = MaterialTheme.typography.titleSmall)
            Text("One-time install of the verified LAB03D synthetic archive into the empty private LAB Mods root. " +
                "Rollback removes only its unmodified synthetic folder and retains a snapshot. " +
                "Interrupted transactions refuse automatic retries. Nothing touches production Stardew Valley.",
                style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(enabled = !busy, onClick = { lab04Action = "INSTALL" },
                    modifier = Modifier.testTag("cbnx06.lab04.request-install")) {
                    Text("Install synthetic mod (LAB)")
                }
                OutlinedButton(enabled = !busy, onClick = { lab04Action = "ROLLBACK" },
                    modifier = Modifier.testTag("cbnx06.lab04.request-rollback")) {
                    Text("Rollback synthetic mod (LAB)")
                }
            }
            lab04Outcome?.let {
                Text(it, modifier = Modifier.testTag("cbnx06.lab04.action-feedback"),
                    style = MaterialTheme.typography.bodySmall)
            }
            lab04Action?.let { action ->
                AlertDialog(
                    onDismissRequest = { lab04Action = null },
                    title = { Text(if (action == "INSTALL") "LAB04 · Confirm synthetic install"
                        else "LAB04 · Confirm synthetic rollback") },
                    text = { Text(if (action == "INSTALL")
                        "Install exactly one verified synthetic test mod in the empty app-private LAB Mods root? " +
                            "This is not a Nexus download or production game installation."
                        else "Remove only the exact unmodified synthetic LAB04 test mod using " +
                            "Cinderbox's snapshot-backed removal? Other contents cause refusal.") },
                    confirmButton = {
                        TextButton(enabled = !busy, onClick = {
                            lab04Action = null
                            busy = true
                            lab03Scope.launch {
                                val result = withContext(Dispatchers.IO) {
                                    runCatching {
                                        if (action == "INSTALL")
                                            NexusLab04SyntheticTransaction.installSynthetic(context)
                                        else NexusLab04SyntheticTransaction.rollbackSynthetic(context)
                                    }
                                }
                                lab04Outcome = result.fold(
                                    onSuccess = { "LAB04 ${it.state} · local SHA-256 ${it.sha256.take(16)}… " +
                                        "· empty root restored: ${it.restoredEmptyRoot} · Nexus unverified" },
                                    onFailure = { "LAB04 REFUSED: ${it.javaClass.simpleName} · no automatic recovery" }
                                )
                                busy = false
                            }
                        }, modifier = Modifier.testTag("cbnx06.lab04.confirm-action")) {
                            Text(if (action == "INSTALL") "Confirm LAB install" else "Confirm LAB rollback")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { lab04Action = null },
                            modifier = Modifier.testTag("cbnx06.lab04.cancel-action")) { Text("Cancel") }
                    }
                )
            }
            HorizontalDivider()
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
                    // LAB03C never emits Cinderbox NXM parameters to a production-capable browser.
                    OutlinedButton(enabled = !busy, onClick = {
                        if (BuildConfig.CBNX_LAB) {
                            lab03cSelection = item // First tap only requests confirmation.
                            lab03cFeedback = null
                        } else {
                            // Production keeps its original user-triggered NXM handoff behavior.
                            busy = true
                            val opened = runCatching {
                                val url = requireNotNull(NexusBrowserHandoff.createUrl(item.modId, item.fileId))
                                NexusBrowserLauncher.open(context, url)
                                check(NexusPairingInbox.resolve(context, item.id, "OPENED"))
                            }
                            if (opened.isFailure) problem = true
                            refreshInbox()
                            busy = false
                        }
                    }, modifier = Modifier.testTag("cbnx03b.handoff.open-exact")) {
                        Text(if (BuildConfig.CBNX_LAB) "Review file page (LAB)" else "Open exact Nexus file")
                    }
                    if (BuildConfig.CBNX_LAB &&
                        NexusLab03CPolicy.reviewUrl(item.modId, item.fileId,
                            item.createdAt, System.currentTimeMillis()) == null) {
                        Text("LAB03C: This request is expired or invalid. Dismiss and request again.",
                            style = MaterialTheme.typography.bodySmall)
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
        // LAB03C: explicit second tap; never treat HTTP inbox admission as browser authorization.
        if (BuildConfig.CBNX_LAB) {
            lab03cSelection?.let { selected ->
                AlertDialog(
                    onDismissRequest = { lab03cSelection = null },
                    title = { Text("LAB03C · Confirm Nexus page") },
                    text = { Text("Open the official Nexus files page for mod ${selected.modId}, " +
                        "file ${selected.fileId}? The file ID is only a page hint. " +
                        "Verify the exact file and complete any Nexus login or requirements yourself. " +
                        "No download, archive or installation is authorized by this action.") },
                    confirmButton = {
                        TextButton(enabled = !busy, onClick = {
                            lab03cSelection = null
                            busy = true
                            val result = runCatching {
                                // Re-read private state at the actual click; no cached/expired open.
                                val current = NexusPairingInbox.list(context).singleOrNull {
                                    it.id == selected.id && it.modId == selected.modId &&
                                        it.fileId == selected.fileId && it.status == "PENDING"
                                }
                                check(current != null) { "LAB03C_REQUEST_NOT_PENDING" }
                                val url = requireNotNull(NexusLab03CPolicy.reviewUrl(
                                    current.modId, current.fileId, current.createdAt,
                                    System.currentTimeMillis())) { "LAB03C_REQUEST_EXPIRED" }
                                check(NexusBrowserLauncher.openLabFilePage(context, url)) {
                                    "LAB03C_NO_SUPPORTED_BROWSER"
                                }
                                check(NexusPairingInbox.resolve(context, current.id, "OPENED")) {
                                    "LAB03C_INBOX_RESOLUTION_FAILED"
                                }
                            }
                            lab03cFeedback = if (result.isSuccess)
                                "LAB03C: Browser launch requested. Nexus page, file, authorization and transfer remain unverified."
                            else
                                "LAB03C: Action refused or not recorded. Check the LAB inbox and browser before retrying."
                            if (result.isFailure) problem = true
                            refreshInbox()
                            busy = false
                        }, modifier = Modifier.testTag("cbnx06.lab03c.confirm-open")) {
                            Text("Open Nexus files page")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { lab03cSelection = null },
                            modifier = Modifier.testTag("cbnx06.lab03c.cancel-open")) {
                            Text("Cancel")
                        }
                    }
                )
            }
            lab03cFeedback?.let {
                Text(it, modifier = Modifier.testTag("cbnx06.lab03c.action-feedback"),
                    style = MaterialTheme.typography.bodySmall)
            }
        }
        if (!inboxError) {
            val resolved = inbox.filter { it.status == "OPENED" || it.status == "DISMISSED" }
                .takeLast(8).asReversed()
            Text("Recent handoffs", style = MaterialTheme.typography.titleSmall)
            if (resolved.isEmpty()) Text("No verified recent history.", style = MaterialTheme.typography.bodySmall)
            for (item in resolved) {
                val action = if (item.status == "OPENED")
                    (if (BuildConfig.CBNX_LAB) "Browser launch requested (page unverified)" else "Opened Nexus page")
                    else "Dismissed"
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
