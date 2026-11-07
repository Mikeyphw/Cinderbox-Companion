package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark

/** UX-09C02: accessible two-row action layout; all handlers are the original callbacks. */
@Composable
fun CinderboxAdvancedModsHeader(
    onBack: () -> Unit,
    onBackups: () -> Unit,
    onUpdates: () -> Unit,
    onBrowse: () -> Unit,
    onImport: () -> Unit
) {
    Column(
        Modifier.fillMaxWidth().background(Dark.Paper)
            .testTag("cinderbox.advanced-mods.header")
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onBack,
                modifier = Modifier.heightIn(min = 48.dp).testTag("cinderbox.advanced-mods.back")) {
                Text("Back", color = Dark.Forest)
            }
            Spacer(Modifier.width(8.dp))
            Column(Modifier.weight(1f)) {
                Text("LOCAL LIBRARY", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall)
                Text("Advanced mods", color = Dark.Ink,
                    style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold))
            }
        }
        Text("Installed mods, profiles and safety tools. Nothing is installed automatically.",
            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CinderboxModsAction("Backups", "backups", onBackups, Modifier.weight(1f))
            CinderboxModsAction("Updates", "updates", onUpdates, Modifier.weight(1f))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            CinderboxModsAction("Browse", "browse", onBrowse, Modifier.weight(1f))
            CinderboxModsAction("Import ZIP", "import", onImport, Modifier.weight(1f))
        }
    }
}

@Composable
private fun CinderboxModsAction(label: String, key: String,
    action: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedButton(onClick = action,
        modifier = modifier.heightIn(min = 48.dp)
            .testTag("cinderbox.advanced-mods.action.$key"),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, Dark.Line),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = Dark.Ink)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

/** Local-first, scrollable empty state; no fabricated installed mods or permissions. */
@Composable
fun CinderboxAdvancedModsEmpty(
    onBrowse: () -> Unit,
    onImportZip: () -> Unit,
    onImportProfile: () -> Unit
) {
    Surface(modifier = Modifier.fillMaxWidth().testTag("cinderbox.advanced-mods.empty"),
        color = Dark.Paper, shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Dark.Line)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("YOUR MOD LIBRARY", color = Dark.Forest,
                style = MaterialTheme.typography.labelSmall)
            Text("No installed mods yet", color = Dark.Ink,
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold))
            Text("Browse community mods or import an archive you trust. You can also import a portable profile.",
                color = Dark.Muted, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(2.dp))
            Button(onClick = onBrowse, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                .testTag("cinderbox.advanced-mods.empty.browse"),
                shape = RoundedCornerShape(12.dp)) { Text("Browse mods") }
            OutlinedButton(onClick = onImportZip,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                    .testTag("cinderbox.advanced-mods.empty.import-zip"),
                shape = RoundedCornerShape(12.dp), border = BorderStroke(1.dp, Dark.Line)) {
                Text("Import ZIP", color = Dark.Ink)
            }
            OutlinedButton(onClick = onImportProfile,
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                    .testTag("cinderbox.advanced-mods.empty.import-profile"),
                shape = RoundedCornerShape(12.dp), border = BorderStroke(1.dp, Dark.Line)) {
                Text("Import profile JSON", color = Dark.Ink)
            }
            Text("Imports require explicit review. No existing mod files are changed by this screen.",
                color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun CinderboxSteamLoginHeader(onBack: () -> Unit) {
    Row(Modifier.fillMaxWidth().background(Dark.Paper)
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .testTag("cinderbox.steam-login.header"),
        verticalAlignment = Alignment.CenterVertically) {
        TextButton(onClick = onBack,
            modifier = Modifier.heightIn(min = 48.dp).testTag("cinderbox.steam-login.back")) {
            Text("Back", color = Dark.Forest)
        }
        Spacer(Modifier.width(10.dp))
        Text("Steam connection", color = Dark.Ink,
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold))
    }
}

@Composable
fun CinderboxSteamLoginIntroduction() {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("OPTIONAL CONNECTION", color = Dark.Forest, style = MaterialTheme.typography.labelSmall)
        Text("Connect your Steam account", color = Dark.Ink,
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold))
        Text("Steam unlocks game downloads and cloud saves. Local mods, saves and backups already work without signing in.",
            color = Dark.Muted, style = MaterialTheme.typography.bodyMedium)
    }
}
