package com.sdvsync.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.sdvsync.mods.models.ModProfile
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.GameDownloadViewModel
import com.sdvsync.ui.viewmodels.ModManagerViewModel
import org.koin.androidx.compose.koinViewModel

/** Read-only UX-08B deep destinations. No install, download, repair or profile application here. */
enum class DeepGameArea { SMAPI, RECOVERY }

data class DeepGameSnapshot(
    val smapiDiscovery: String = "Not observed",
    val storedSmapiVersion: String? = null,
    val availableSmapiVersion: String? = null,
    val smapiUpdateSuggested: Boolean = false,
    val hasRecoverableDownload: Boolean = false,
    val protectedUpdateNeedsReview: Boolean = false
)

@Composable
fun ApprovedGameDeepScreen(
    area: DeepGameArea,
    onBack: () -> Unit,
    onOpenInstallationHealth: () -> Unit,
    onReviewAdvancedSetup: () -> Unit,
    onOpenOperations: () -> Unit,
    viewModel: GameDownloadViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsState()
    ApprovedGameDeepContent(
        area = area,
        observation = DeepGameSnapshot(
            smapiDiscovery = state.primarySmapiStatus.name.replace('_', ' '),
            storedSmapiVersion = state.installedSmapiVersion,
            availableSmapiVersion = state.latestSmapiVersion,
            smapiUpdateSuggested = state.smapiUpdateAvailable,
            hasRecoverableDownload = state.hasRecoverableDownload,
            protectedUpdateNeedsReview = !state.protectedUpdateStatus.isNullOrBlank()
        ),
        onBack = onBack,
        onOpenInstallationHealth = onOpenInstallationHealth,
        onReviewAdvancedSetup = onReviewAdvancedSetup,
        onOpenOperations = onOpenOperations
    )
}

@Composable
private fun DeepToolsHeading(kicker: String, title: String, explanation: String, onBack: () -> Unit) {
    TextButton(onClick = onBack, modifier = Modifier.testTag("cinderbox.deep-tools.back")) {
        Text("‹ Back", color = Dark.Forest)
    }
    Text(kicker, color = Dark.Forest, style = MaterialTheme.typography.labelSmall)
    Text(title, color = Dark.Ink,
        style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
        modifier = Modifier.semantics { heading() })
    Text(explanation, color = Dark.Muted, style = MaterialTheme.typography.bodyMedium)
}

@Composable
private fun DeepToolsFinding(title: String, observation: String, provenance: String) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(title, color = Dark.Ink,
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold))
        Text(observation, color = Dark.Forest,
            style = MaterialTheme.typography.bodyMedium, maxLines = 3,
            overflow = TextOverflow.Ellipsis)
        Text(provenance, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
    }
    HorizontalDivider(color = Dark.Line)
}

@Composable
fun ApprovedGameDeepContent(
    area: DeepGameArea,
    observation: DeepGameSnapshot,
    onBack: () -> Unit,
    onOpenInstallationHealth: () -> Unit,
    onReviewAdvancedSetup: () -> Unit,
    onOpenOperations: () -> Unit
) {
    val smapi = area == DeepGameArea.SMAPI
    Column(Modifier.fillMaxSize().background(Dark.Background)
        .testTag(if (smapi) "cinderbox.screen.smapi-overview" else "cinderbox.screen.recovery-overview")
        .verticalScroll(rememberScrollState())
        .padding(horizontal = 18.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        DeepToolsHeading(
            kicker = if (smapi) "MODDING ENVIRONMENT" else "STORAGE & RECOVERY",
            title = if (smapi) "SMAPI status" else "Recovery status",
            explanation = if (smapi)
                "Observed loader metadata and discovery only. Runtime support and file integrity are not verified."
            else "Review known recovery indicators. This page never retries, repairs, replaces or deletes files.",
            onBack = onBack
        )
        Surface(color = Dark.Paper, shape = RoundedCornerShape(17.dp),
            border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
            Column {
                if (smapi) {
                    DeepToolsFinding("SMAPI discovery", observation.smapiDiscovery,
                        "Filesystem candidate only; not version or integrity verification")
                    DeepToolsFinding("Stored loader version", observation.storedSmapiVersion ?: "Not recorded",
                        "App-maintained metadata; not a live runtime attestation")
                    DeepToolsFinding("Available release metadata", observation.availableSmapiVersion ?: "Unknown",
                        "Release metadata may be unavailable or stale")
                    DeepToolsFinding("Update advisory",
                        if (observation.smapiUpdateSuggested) "Review suggested" else "No verified update conclusion",
                        "No update or download is started from this view")
                } else {
                    DeepToolsFinding("Interrupted download evidence",
                        if (observation.hasRecoverableDownload) "Recovery candidate reported"
                        else "No recovery candidate reported",
                        "App-owned download journal; absence does not guarantee clean files")
                    DeepToolsFinding("Protected update status",
                        if (observation.protectedUpdateNeedsReview) "Review required"
                        else "No protected-update status reported",
                        "No paths, filenames, tokens or raw journal errors shown")
                    DeepToolsFinding("Recovery qualification", "Not verified",
                        "Status detection is not proof that a rollback or repair succeeded")
                }
            }
        }
        Text("A real Android/game installation needs independent device qualification. " +
            "Existing service-layer guards still control all file changes.",
            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
        Button(onClick = onOpenInstallationHealth, modifier = Modifier.fillMaxWidth()
            .testTag("cinderbox.deep-tools.health")) { Text("Inspect installation health") }
        OutlinedButton(onClick = onReviewAdvancedSetup, modifier = Modifier.fillMaxWidth()
            .testTag("cinderbox.deep-tools.advanced")) { Text("Review advanced setup") }
        OutlinedButton(onClick = onOpenOperations, modifier = Modifier.fillMaxWidth()) {
            Text("Open Operation center")
        }
    }
}

@Composable
fun ApprovedProfileDetailScreen(
    profileId: String,
    onBack: () -> Unit,
    onReviewAdvancedManager: () -> Unit,
    viewModel: ModManagerViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsState()
    // Refuse ambiguous or stale identities; never silently display another profile.
    val matches = state.profiles.filter { it.id == profileId }
    val profile = matches.singleOrNull()
    ApprovedProfileDetailContent(profile, state.isLoading,
        state.activeProfileName == profile?.name && profile != null,
        onBack, onReviewAdvancedManager)
}

@Composable
fun ApprovedProfileDetailContent(
    profile: ModProfile?,
    isLoading: Boolean,
    matchesCurrentEnabledSet: Boolean,
    onBack: () -> Unit,
    onReviewAdvancedManager: () -> Unit
) {
    Column(Modifier.fillMaxSize().background(Dark.Background)
        .testTag("cinderbox.screen.profile-detail")
        .verticalScroll(rememberScrollState())
        .padding(horizontal = 18.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        DeepToolsHeading("MOD PROFILES", "Profile details",
            "Read-only saved loadout. Nothing is applied just by opening this screen.", onBack)
        if (profile == null) {
            Surface(color = Dark.Paper, shape = RoundedCornerShape(17.dp),
                border = BorderStroke(1.dp, Dark.Line)) {
                Column(Modifier.padding(15.dp)) {
                    Text(if (isLoading) "Loading profile" else "Profile unavailable",
                        color = Dark.Ink)
                    Text("The saved profile may be missing or its identifier may have changed.",
                        color = Dark.Muted)
                }
            }
        } else {
            Surface(color = Dark.Paper, shape = RoundedCornerShape(17.dp),
                border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
                Column {
                    DeepToolsFinding("Saved profile", profile.name, "Local profile metadata")
                    DeepToolsFinding("Desired enabled mods", profile.enabledModIds.size.toString(),
                        "Saved identifiers; presence and compatibility are not assumed")
                    DeepToolsFinding("Protection", if (profile.isProtected) "Protected" else "Standard",
                        "Protected profiles cannot be silently overwritten")
                    DeepToolsFinding("Enabled-set comparison",
                        if (matchesCurrentEnabledSet) "Matches observed enabled set"
                        else "Not confirmed as current",
                        "A matching set is not proof of an applied profile or runtime compatibility")
                }
            }
            if (profile.description.isNotBlank()) {
                Text("Description", color = Dark.Ink,
                    style = MaterialTheme.typography.titleMedium)
                Text(profile.description, color = Dark.Muted,
                    style = MaterialTheme.typography.bodyMedium)
            }
            Text("Selected mod IDs", color = Dark.Ink,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            if (profile.enabledModIds.isEmpty()) {
                Text("No selected mods", color = Dark.Muted)
            } else {
                val identifiers = profile.enabledModIds.sorted()
                Surface(color = Dark.Paper, shape = RoundedCornerShape(17.dp),
                    border = BorderStroke(1.dp, Dark.Line), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        identifiers.take(40).forEach { id ->
                            Text("• " + id, color = Dark.Ink,
                                style = MaterialTheme.typography.bodySmall)
                        }
                        if (identifiers.size > 40) Text(
                            "${identifiers.size - 40} additional saved IDs; open manager to review.",
                            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        Button(onClick = onReviewAdvancedManager, modifier = Modifier.fillMaxWidth()
            .testTag("cinderbox.profile-detail.review")) {
            Text("Review in advanced mod manager")
        }
        Text("Profiles can be previewed and applied only through the existing reviewed workflow.",
            color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
    }
}
