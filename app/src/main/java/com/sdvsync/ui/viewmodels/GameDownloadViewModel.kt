package com.sdvsync.ui.viewmodels

import android.content.Context
import android.os.Environment
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sdvsync.R
import com.sdvsync.cinderbox.CinderboxPaths
import com.sdvsync.download.CinderboxDownloadProgress
import com.sdvsync.download.DownloadProgress
import com.sdvsync.download.GameDownloadManager
import com.sdvsync.local.InstallationScanner
import com.sdvsync.local.InstallAssessment
import com.sdvsync.local.InstallHealth
import com.sdvsync.local.StoragePreflight
import java.io.File
import com.sdvsync.download.GitHubReleaseChecker
import com.sdvsync.download.SmapiSetupProgress
import com.sdvsync.fileaccess.FileAccessDetector
import com.sdvsync.logging.AppLogger
import com.sdvsync.steam.ConnectionState
import com.sdvsync.steam.SteamAuthenticator
import com.sdvsync.steam.SteamClientManager
import com.sdvsync.steam.SteamContentService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class CinderboxWizardStep {
    SETUP_CHOICE,
    PERMISSIONS,
    DOWNLOAD_APK,
    INSTALL_APK,
    VERIFY_LAUNCHED,
    READY
}

data class CinderboxWizardState(
    val isVisible: Boolean = false,
    val currentStep: CinderboxWizardStep = CinderboxWizardStep.SETUP_CHOICE,
    val hasStoragePermission: Boolean = false,
    val hasInstallPermission: Boolean = false,
    val cinderboxDirExists: Boolean = false
)

data class GameDownloadState(
    val isLoadingBranches: Boolean = false,
    val branches: List<SteamContentService.BranchInfo> = emptyList(),
    val selectedBranch: String = "public",
    val branchPassword: String = "",
    val selectedOs: String = "windows",
    val installDirectory: String = "",
    val selectedInstallHealth: InstallAssessment? = null,
    val storageReady: Boolean = false,
    val storageDetail: String = "Storage not checked",
    val verifyAfterDownload: Boolean = true,
    val downloadProgress: DownloadProgress = DownloadProgress(),
    val smapiSetupProgress: SmapiSetupProgress = SmapiSetupProgress(),
    val cinderboxDownloadProgress: CinderboxDownloadProgress = CinderboxDownloadProgress(),
    val error: String? = null,
    val branchLoadError: String? = null,
    val branchLoadNeedsReconnect: Boolean = false,
    val steamLoggedIn: Boolean = false,
    val cinderboxUpdateAvailable: Boolean = false,
    val latestCinderboxVersion: String? = null,
    val installedCinderboxVersion: String? = null,
    val smapiUpdateAvailable: Boolean = false,
    val latestSmapiVersion: String? = null,
    val installedSmapiVersion: String? = null,
    val isCinderboxSetup: Boolean = false
)

class GameDownloadViewModel(
    private val context: Context,
    private val contentService: SteamContentService,
    private val downloadManager: GameDownloadManager,
    private val fileAccessDetector: FileAccessDetector,
    private val releaseChecker: GitHubReleaseChecker,
    private val steamClientManager: SteamClientManager,
    private val steamAuthenticator: SteamAuthenticator
) : ViewModel() {

    companion object {
        private const val TAG = "GameDownloadVM"
        const val SETUP_TYPE_CINDERBOX = "cinderbox"
        const val SETUP_TYPE_OTHER = "other"
    }

    private val _state = MutableStateFlow(GameDownloadState())
    val state: StateFlow<GameDownloadState> = _state.asStateFlow()
    private val _wizardState = MutableStateFlow(CinderboxWizardState())
    val wizardState: StateFlow<CinderboxWizardState> = _wizardState.asStateFlow()
    private var branchLoadJob: Job? = null
    private var smapiJob: Job? = null
    private var cinderboxJob: Job? = null
    private var pendingSetupType: String? = null

    init {
        val defaultDir = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS
        ).resolve("StardewValley").absolutePath
        val savedDir = context.getSharedPreferences("m4_local_install", Context.MODE_PRIVATE)
            .getString("game_dir", null) ?: defaultDir
        _state.value = _state.value.copy(
            installDirectory = savedDir,
            selectedInstallHealth = InstallationScanner.game(File(savedDir)),
            storageReady = StoragePreflight.check(File(savedDir)).writable,
            storageDetail = StoragePreflight.check(File(savedDir)).details,
            isCinderboxSetup = fileAccessDetector.getSetupType() == SETUP_TYPE_CINDERBOX
        )

        // Keep download eligibility in sync with the live Steam transport state.
        viewModelScope.launch {
            steamClientManager.connectionState.collect { connection ->
                _state.update { it.copy(steamLoggedIn = connection == ConnectionState.LOGGED_IN) }
            }
        }
        viewModelScope.launch {
            downloadManager.progress.collect { progress ->
                _state.value = _state.value.copy(downloadProgress = progress)
            }
        }
        viewModelScope.launch {
            downloadManager.smapiProgress.collect { progress ->
                _state.value = _state.value.copy(smapiSetupProgress = progress)
                if (progress.completed) refreshInstalledVersions()
            }
        }
        viewModelScope.launch {
            downloadManager.cinderboxProgress.collect { progress ->
                _state.value = _state.value.copy(cinderboxDownloadProgress = progress)
            }
        }

        // Check for updates
        viewModelScope.launch {
            try {
                val cinderboxRelease = releaseChecker.getLatestRelease(
                    GitHubReleaseChecker.CINDERBOX_REPO,
                    GitHubReleaseChecker.CINDERBOX_ASSET_PATTERN
                )
                val installedCinderbox = releaseChecker.getInstalledVersion(GitHubReleaseChecker.KEY_CINDERBOX_VERSION)

                val smapiRelease = releaseChecker.getLatestRelease(
                    GitHubReleaseChecker.SMAPI_REPO,
                    GitHubReleaseChecker.SMAPI_ASSET_PATTERN
                )
                val installedSmapi = releaseChecker.getInstalledVersion(GitHubReleaseChecker.KEY_SMAPI_VERSION)

                _state.value = _state.value.copy(
                    latestCinderboxVersion = cinderboxRelease?.version,
                    installedCinderboxVersion = installedCinderbox,
                    cinderboxUpdateAvailable = releaseChecker.isUpdateAvailable(
                        installedCinderbox,
                        cinderboxRelease?.version
                    ),
                    latestSmapiVersion = smapiRelease?.version,
                    installedSmapiVersion = installedSmapi,
                    smapiUpdateAvailable = releaseChecker.isUpdateAvailable(
                        installedSmapi,
                        smapiRelease?.version
                    )
                )
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to check for updates", e)
            }
        }
    }

    fun refreshInstalledVersions() {
        val cinderbox = releaseChecker.getInstalledVersion(GitHubReleaseChecker.KEY_CINDERBOX_VERSION)
        val smapi = releaseChecker.getInstalledVersion(GitHubReleaseChecker.KEY_SMAPI_VERSION)
        _state.update {
            it.copy(
                installedCinderboxVersion = cinderbox,
                installedSmapiVersion = smapi,
                cinderboxUpdateAvailable = releaseChecker.isUpdateAvailable(cinderbox, it.latestCinderboxVersion),
                smapiUpdateAvailable = releaseChecker.isUpdateAvailable(smapi, it.latestSmapiVersion)
            )
        }
    }

    /** Initial load is read-only; user Retry may resume the previously saved Steam session. */
    fun loadBranches(reconnect: Boolean = false) {
        // Prevent overlapping PICS jobs and competing saved-session reconnect attempts.
        if (branchLoadJob?.isActive == true) return
        branchLoadJob = viewModelScope.launch {
            _state.update {
                it.copy(
                    isLoadingBranches = true,
                    branchLoadError = null,
                    branchLoadNeedsReconnect = false
                )
            }
            try {
                if (!steamClientManager.isLoggedIn) {
                    if (reconnect && steamClientManager.connectionState.value != ConnectionState.CONNECTING) {
                        AppLogger.i(TAG, "User requested saved-session Steam reconnect")
                        steamAuthenticator.loginWithSavedSession()
                    }
                    // Login and Steam transport callbacks are asynchronous. Never call PICS
                    // until SteamClientManager itself reports a completed Steam logon.
                    val timeoutMs = if (reconnect) 30_000L else 7_000L
                    if (!steamClientManager.awaitLoggedIn(timeoutMs)) {
                        _state.update {
                            it.copy(
                                isLoadingBranches = false,
                                branchLoadNeedsReconnect = true,
                                branchLoadError = context.getString(R.string.download_error_steam_offline)
                            )
                        }
                        return@launch
                    }
                }

                val info = contentService.getAppBranches()
                if (info.branches.isEmpty()) {
                    _state.update {
                        it.copy(
                            branches = emptyList(),
                            isLoadingBranches = false,
                            branchLoadError = context.getString(R.string.download_error_no_branches)
                        )
                    }
                } else {
                    _state.update { current ->
                        val selected = current.selectedBranch.takeIf { selected ->
                            info.branches.any { it.name == selected }
                        } ?: info.branches.firstOrNull { it.name == "public" }?.name
                            ?: info.branches.first().name
                        current.copy(
                            branches = info.branches,
                            selectedBranch = selected,
                            isLoadingBranches = false,
                            branchLoadError = null,
                            branchLoadNeedsReconnect = false
                        )
                    }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to load branches", e)
                val disconnected = !steamClientManager.isLoggedIn
                _state.update {
                    it.copy(
                        isLoadingBranches = false,
                        branchLoadNeedsReconnect = disconnected,
                        branchLoadError = if (disconnected) {
                            context.getString(R.string.download_error_steam_offline)
                        } else {
                            // Do not display raw Steam exceptions, which may include private data.
                            context.getString(R.string.download_error_load_branches, e.javaClass.simpleName)
                        }
                    )
                }
            }
        }
    }

    fun retryBranchLoad() = loadBranches(reconnect = true)

    fun selectBranch(name: String) {
        _state.value = _state.value.copy(selectedBranch = name, branchPassword = "")
    }

    fun selectOs(os: String) {
        _state.value = _state.value.copy(selectedOs = os)
    }

    fun updateInstallDirectory(path: String) {
        context.getSharedPreferences("m4_local_install", Context.MODE_PRIVATE)
            .edit().putString("game_dir", path).apply()
        _state.value = _state.value.copy(
            installDirectory = path,
            selectedInstallHealth = InstallationScanner.game(File(path)),
            storageReady = StoragePreflight.check(File(path)).writable,
            storageDetail = StoragePreflight.check(File(path)).details
        )
    }

    fun refreshSelectedDirectoryHealth() {
        val path = _state.value.installDirectory
        _state.value = _state.value.copy(
            selectedInstallHealth = InstallationScanner.game(File(path)),
            storageReady = StoragePreflight.check(File(path)).writable,
            storageDetail = StoragePreflight.check(File(path)).details
        )
    }

    fun updateBranchPassword(password: String) {
        _state.value = _state.value.copy(branchPassword = password)
    }

    fun toggleVerification() {
        _state.value = _state.value.copy(verifyAfterDownload = !_state.value.verifyAfterDownload)
    }

    fun startDownload() {
        // A cached branch must never authorize a download after Steam disconnects.
        if (!steamClientManager.isLoggedIn) {
            _state.update {
                it.copy(
                    branchLoadNeedsReconnect = true,
                    branchLoadError = context.getString(R.string.download_error_steam_offline)
                )
            }
            return
        }
        val current = _state.value
        if (current.installDirectory.isBlank()) {
            _state.value = current.copy(error = context.getString(R.string.download_error_no_directory))
            return
        }

        val selectedHealth = InstallationScanner.game(File(current.installDirectory))
        val storage = StoragePreflight.check(File(current.installDirectory))
        if (!storage.writable || selectedHealth.health == InstallHealth.INACCESSIBLE ||
            selectedHealth.health == InstallHealth.INCOMPLETE ||
            selectedHealth.health == InstallHealth.STRUCTURALLY_VALID ||
            selectedHealth.health == InstallHealth.DETECTED) {
            _state.value = current.copy(error = if (!storage.writable) storage.details else
                "Existing game files detected (${selectedHealth.health}). Choose an empty destination; M4 never overwrites existing installations.")
            return
        }
        val selectedBranchInfo = current.branches.find { it.name == current.selectedBranch }
        if (selectedBranchInfo?.passwordRequired == true && current.branchPassword.isBlank()) {
            _state.value = current.copy(error = context.getString(R.string.download_error_password_required))
            return
        }

        // Persist any pending setup choice now that validation passed
        pendingSetupType?.let { type ->
            fileAccessDetector.setSetupCompleted(type)
            pendingSetupType = null
        }

        _state.value = current.copy(error = null)

        try {
            downloadManager.startDownload(
                branch = current.selectedBranch,
                branchPassword = current.branchPassword.ifBlank { null },
                installDirectory = current.installDirectory,
                os = current.selectedOs,
                verifyAfterDownload = current.verifyAfterDownload
            )
        } catch (e: IllegalStateException) {
            _state.value = _state.value.copy(error = e.message ?: "Storage is unavailable")
        }
    }

    fun cancelDownload() {
        downloadManager.cancelDownload()
    }

    fun dismissError() {
        _state.value = _state.value.copy(error = null)
    }

    fun copyCinderbox() {
        downloadManager.resetCopyState()
        viewModelScope.launch {
            try {
                downloadManager.copyToCinderbox(_state.value.installDirectory)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Cinderbox copy failed", e)
                downloadManager.setCopyError(e.message ?: "Copy failed unexpectedly")
            }
        }
    }

    fun resetDownload() {
        downloadManager.resetProgress()
    }

    fun extractSmapi() {
        if (smapiJob?.isActive == true) return
        smapiJob = viewModelScope.launch {
            try {
                downloadManager.downloadAndExtractSmapi()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "SMAPI download/extraction failed", e)
            }
        }
    }

    fun resetSmapiSetup() {
        downloadManager.resetSmapiProgress()
    }

    fun downloadCinderbox() {
        if (cinderboxJob?.isActive == true) return
        cinderboxJob = viewModelScope.launch {
            try {
                downloadManager.downloadCinderboxApk()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Cinderbox download failed", e)
            }
        }
    }

    fun resetCinderboxDownload() {
        downloadManager.resetCinderboxProgress()
    }

    // ── Cinderbox Wizard ──────────────────────────────────────────────────

    fun onDownloadButtonClicked() {
        // Already completed setup before — skip wizard
        if (fileAccessDetector.isSetupCompleted()) {
            startDownload()
            return
        }

        // Cinderbox dir already exists — user clearly has it installed
        if (CinderboxPaths.isInstalled()) {
            fileAccessDetector.setSetupCompleted(SETUP_TYPE_CINDERBOX)
            fileAccessDetector.setCinderboxMode(true)
            _state.value = _state.value.copy(isCinderboxSetup = true)
            startDownload()
            return
        }

        // Show wizard
        _wizardState.value = CinderboxWizardState(isVisible = true)
    }

    fun onWizardChooseCinderbox() {
        val dirExists = CinderboxPaths.isInstalled()
        if (dirExists) {
            // Already installed — jump to ready
            _wizardState.value = _wizardState.value.copy(
                currentStep = CinderboxWizardStep.READY,
                cinderboxDirExists = true
            )
        } else {
            // Need to check permissions first
            _wizardState.value = _wizardState.value.copy(
                currentStep = CinderboxWizardStep.PERMISSIONS
            )
        }
    }

    fun onWizardChooseOther() {
        pendingSetupType = SETUP_TYPE_OTHER
        _state.value = _state.value.copy(isCinderboxSetup = false)
        _wizardState.value = CinderboxWizardState()
        startDownload()
    }

    fun refreshPermissions(hasStorage: Boolean, hasInstall: Boolean) {
        val current = _wizardState.value
        val updated = current.copy(
            hasStoragePermission = hasStorage,
            hasInstallPermission = hasInstall
        )
        _wizardState.value = updated

        // Auto-advance when both permissions granted
        if (updated.hasStoragePermission &&
            updated.hasInstallPermission &&
            current.currentStep == CinderboxWizardStep.PERMISSIONS
        ) {
            _wizardState.value = updated.copy(
                currentStep = CinderboxWizardStep.DOWNLOAD_APK
            )
            // Auto-trigger download
            downloadCinderbox()
        }
    }

    fun onApkDownloadComplete() {
        val current = _wizardState.value
        if (current.currentStep == CinderboxWizardStep.DOWNLOAD_APK) {
            _wizardState.value = current.copy(
                currentStep = CinderboxWizardStep.INSTALL_APK
            )
        }
    }

    fun onApkInstalled() {
        _wizardState.value = _wizardState.value.copy(
            currentStep = CinderboxWizardStep.VERIFY_LAUNCHED
        )
    }

    fun checkCinderboxDirectory(): Boolean {
        val exists = CinderboxPaths.isInstalled()
        if (exists) {
            _wizardState.value = _wizardState.value.copy(
                currentStep = CinderboxWizardStep.READY,
                cinderboxDirExists = true
            )
        }
        return exists
    }

    fun skipVerification() {
        _wizardState.value = _wizardState.value.copy(
            currentStep = CinderboxWizardStep.READY
        )
    }

    fun onWizardStartDownload() {
        fileAccessDetector.setSetupCompleted(SETUP_TYPE_CINDERBOX)
        fileAccessDetector.setCinderboxMode(true)
        _state.value = _state.value.copy(isCinderboxSetup = true)
        _wizardState.value = CinderboxWizardState()
        startDownload()
    }

    fun dismissWizard() {
        cinderboxJob?.cancel()
        cinderboxJob = null
        resetCinderboxDownload()
        _wizardState.value = CinderboxWizardState()
    }
}
