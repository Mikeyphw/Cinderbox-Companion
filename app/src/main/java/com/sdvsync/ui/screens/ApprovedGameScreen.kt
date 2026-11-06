package com.sdvsync.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.sdvsync.local.M23InstallationDiscovery
import com.sdvsync.ui.policy.R43DDestinationPresentation
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark
import com.sdvsync.ui.viewmodels.GameDownloadViewModel
import org.koin.androidx.compose.koinViewModel

/**
 * UX-03: the approved native dark Game tab. Data comes from read-only discovery,
 * NOT from demo inventory or Steam entitlement inference. This component never
 * performs downloads, chooses filesystem destinations, or authorizes game writes.
 * The existing setup screen remains reachable behind a deliberate navigation.
 */
@Composable
fun ApprovedGameScreen(
    isSteamConnected: Boolean,
    onConnectSteam: () -> Unit,
    onOpenInstallationHealth: () -> Unit,
    onOpenGameSetup: () -> Unit,
    onOpenOperationCenter: () -> Unit,
    onOpenSmapi: () -> Unit = {},
    onOpenRecovery: () -> Unit = {},
    viewModel: GameDownloadViewModel = koinViewModel()
) {
    val state by viewModel.state.collectAsState()
    LifecycleResumeEffect(viewModel) {
        viewModel.refreshInstalledVersions()
        viewModel.refreshSelectedDirectoryHealth()
        viewModel.refreshProtectedUpdateStatus()
        onPauseOrDispose {}
    }
    val location = R43DDestinationPresentation.from(
        state.fixedDestinationCode, state.primaryGameStatus, state.protectedUpdateStatus)
    val gameFound = state.primaryGameStatus == M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED
    val smapiFound = state.primarySmapiStatus == M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED

    Column(Modifier.fillMaxSize().background(Dark.Background).testTag("cinderbox.screen.game")
        .verticalScroll(rememberScrollState()).padding(horizontal = 18.dp)) {
        Spacer(Modifier.height(10.dp))
        GameTopBar(onOpenOperationCenter)
        Spacer(Modifier.height(20.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("PLAY, INSTALL, MAINTAIN", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.1.sp))
                Text("Game", color = Dark.Ink,
                    style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold, fontSize = 25.sp),
                    modifier = Modifier.semantics { heading() })
                Text("Keep your installation healthy.", color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
            }
            Surface(color = Dark.Mint, shape = RoundedCornerShape(24.dp)) {
                Text("Local checks", color = Dark.Forest,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                    style = MaterialTheme.typography.labelSmall)
            }
        }
        Spacer(Modifier.height(18.dp))
        Surface(Modifier.fillMaxWidth(), color = Dark.Paper, shape = RoundedCornerShape(20.dp),
            border = BorderStroke(1.dp, Dark.Line)) {
            Column {
                GameLandscape()
                Column(Modifier.padding(14.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("Stardew Valley", color = Dark.Ink,
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
                            Text(if (gameFound) "Local installation candidate · Not verified"
                                 else "Local installation · ${R43DDestinationPresentation.installedLabel(state.primaryGameStatus)}",
                                color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                        }
                        Surface(color = if (gameFound) Dark.Mint else Dark.Paper2,
                            shape = RoundedCornerShape(22.dp)) {
                            Text(if (gameFound) "Found" else "Check needed", color = if (gameFound) Dark.Forest else Dark.Muted,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                                style = MaterialTheme.typography.labelSmall)
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Box(Modifier.fillMaxWidth().height(1.dp).background(Dark.Line))
                    Spacer(Modifier.height(12.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("GAME VERSION", color = Dark.Muted,
                                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp))
                            Text("Not verified", color = Dark.Ink,
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold))
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("SMAPI", color = Dark.Muted, style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp))
                            Text(if (smapiFound) "Found, not verified" else "Check required", color = Dark.Ink,
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold))
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        GameSmallAction("Installation health", onOpenInstallationHealth, Modifier.weight(1f), filled = true)
                        GameSmallAction("Files", onOpenInstallationHealth, Modifier.weight(1f))
                    }
                }
            }
        }
        Spacer(Modifier.height(20.dp))
        GameSection("Install & download")
        Spacer(Modifier.height(10.dp))
        Surface(Modifier.fillMaxWidth(), color = Dark.Paper,
            shape = RoundedCornerShape(20.dp), border = BorderStroke(1.dp, Dark.Line)) {
            Column(Modifier.padding(15.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(40.dp).clip(RoundedCornerShape(13.dp)).background(Dark.WarnBackground),
                        contentAlignment = Alignment.Center) {
                        Text("⇩", fontSize = 23.sp, color = Dark.Accent)
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Steam game download", color = Dark.Ink,
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                        Text("Official download and branch selection", color = Dark.Muted,
                            style = MaterialTheme.typography.bodySmall)
                    }
                    Surface(shape = RoundedCornerShape(22.dp),
                        color = if (isSteamConnected) Dark.Mint else Dark.WarnBackground) {
                        Text(if (isSteamConnected) "Check access" else "Steam needed",
                            color = if (isSteamConnected) Dark.Forest else Dark.Warn,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp),
                            style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp))
                    }
                }
                Spacer(Modifier.height(13.dp))
                Text(if (isSteamConnected)
                    "Steam is connected. Game entitlement, access and storage still require verification."
                    else "Connect Steam when you want to download game files. No login is required to use the rest of Cinderbox.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(12.dp))
                Button(onClick = if (isSteamConnected) onOpenGameSetup else onConnectSteam,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 45.dp)
                        .testTag("cinderbox.game.download-action"),
                    colors = ButtonDefaults.buttonColors(containerColor = Dark.Mint, contentColor = Dark.Ink),
                    shape = RoundedCornerShape(11.dp)) {
                    Text(if (isSteamConnected) "Review download requirements" else "Connect Steam to download",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold))
                }
            }
        }
        Spacer(Modifier.height(20.dp))
        GameSection("Modding environment")
        Spacer(Modifier.height(10.dp))
        Surface(Modifier.fillMaxWidth(), color = Dark.Paper, shape = RoundedCornerShape(18.dp),
            border = BorderStroke(1.dp, Dark.Line)) {
            Column(Modifier.padding(15.dp)) {
                Text("SMAPI & game support", color = Dark.Ink,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                Spacer(Modifier.height(6.dp))
                Text("SMAPI: ${R43DDestinationPresentation.installedLabel(state.primarySmapiStatus)}",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Text("Detection is not compatibility or file-integrity verification.",
                    color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(10.dp))
                GameSmallAction("Check modding setup", onOpenSmapi, Modifier.fillMaxWidth())
            }
        }
        Spacer(Modifier.height(20.dp))
        GameSection("Storage & recovery")
        Spacer(Modifier.height(10.dp))
        Surface(Modifier.fillMaxWidth(), color = Dark.Paper,
            shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, Dark.Line)) {
            Column(Modifier.padding(15.dp)) {
                Text(location.title, color = Dark.Ink,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                Spacer(Modifier.height(4.dp))
                Text(location.detail, color = Dark.Muted, style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(8.dp))
                Text("Existing game files, saves and mods remain protected.", color = Dark.Muted,
                    style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(10.dp))
                GameSmallAction("View setup & recovery", onOpenRecovery, Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                GameSmallAction("Advanced game setup", onOpenGameSetup, Modifier.fillMaxWidth())
            }
        }
        Spacer(Modifier.height(28.dp))
    }
}

@Composable
private fun GameTopBar(onOpenOperationCenter: () -> Unit) {
    Row(Modifier.fillMaxWidth().height(49.dp).testTag("cinderbox.shell.game-topbar"),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(36.dp).clip(RoundedCornerShape(13.dp)).background(Dark.Mint),
                contentAlignment = Alignment.Center) {
                Text("♨", color = Dark.Accent, fontSize = 22.sp)
            }
            Spacer(Modifier.width(9.dp))
            Column {
                Text("Cinderbox", color = Dark.Ink,
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
                Text("GAME & LAUNCHER", color = Dark.Muted,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp))
            }
        }
        Text("Activity", color = Dark.Forest, style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.clickable(onClick = onOpenOperationCenter)
                .padding(9.dp).testTag("cinderbox.game.activity"))
    }
}

@Composable
private fun GameLandscape() {
    Canvas(Modifier.fillMaxWidth().height(133.dp).testTag("cinderbox.game.cover")) {
        drawRect(Color(0xFF57846F))
        val middle = Path().apply {
            moveTo(0f, size.height)
            cubicTo(size.width * .27f, size.height * .58f,
                size.width * .69f, size.height * .31f,
                size.width, size.height * .41f)
            lineTo(size.width, size.height)
            close()
        }
        drawPath(middle, Color(0xFF8DB4A2))
        val centerX = size.width * .5f
        val centerY = size.height * .52f
        val mountain = Path().apply {
            moveTo(centerX - 28.dp.toPx(), centerY + 15.dp.toPx())
            lineTo(centerX - 5.dp.toPx(), centerY - 23.dp.toPx())
            lineTo(centerX + 4.dp.toPx(), centerY - 4.dp.toPx())
            lineTo(centerX + 14.dp.toPx(), centerY - 15.dp.toPx())
            lineTo(centerX + 32.dp.toPx(), centerY + 15.dp.toPx())
            close()
        }
        drawPath(mountain, Dark.Ink, style = androidx.compose.ui.graphics.drawscope.Stroke(width = 4.dp.toPx()))
    }
}

@Composable
private fun GameSection(text: String) {
    Text(text, color = Dark.Ink,
        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, fontSize = 16.sp),
        modifier = Modifier.semantics { heading() })
}

@Composable
private fun GameSmallAction(text: String, onClick: () -> Unit, modifier: Modifier, filled: Boolean = false) {
    if (filled) {
        Button(onClick = onClick, modifier = modifier.heightIn(min = 44.dp),
            shape = RoundedCornerShape(11.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Dark.Mint, contentColor = Dark.Ink)) {
            Text(text, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                textAlign = TextAlign.Center)
        }
    } else {
        OutlinedButton(onClick = onClick, modifier = modifier.heightIn(min = 44.dp),
            shape = RoundedCornerShape(11.dp), border = BorderStroke(1.dp, Dark.Line)) {
            Text(text, color = Dark.Ink, style = MaterialTheme.typography.labelSmall,
                textAlign = TextAlign.Center)
        }
    }
}
