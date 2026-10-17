package com.sdvsync.local

import com.sdvsync.cinderbox.CinderboxPaths
import java.io.File

/** Detection is read-only; a directory's presence is never proof of file integrity. */
enum class InstallHealth { MISSING, INACCESSIBLE, INCOMPLETE, DETECTED, STRUCTURALLY_VALID }

data class InstallAssessment(val health: InstallHealth, val details: String, val location: String) {
    // A structure check without a trusted Steam depot manifest never authorizes use.
    val usable: Boolean get() = false
}

data class InstallationSnapshot(
    val selectedGame: InstallAssessment,
    val cinderboxGame: InstallAssessment,
    val smapi: InstallAssessment,
    val cinderboxApp: InstallAssessment,
    val storage: StorageCheck,
    val discovery: M23InstallationDiscovery.Inventory? = null
)

/** Never follows a symlink in a directory being evaluated for direct modification. */
object InstallationScanner {
    /** Legacy UI API, now backed by the bounded M23 evidence engine. */
    fun game(folder: File): InstallAssessment {
        val wrapped = File(folder, "Stardew Valley")
        val root = if (wrapped.isDirectory &&
            !File(folder, "Stardew Valley.dll").exists()) wrapped else folder
        val observed = M23InstallationDiscovery.game(root)
        val location = root.absolutePath
        return when (observed.status) {
            M23InstallationDiscovery.Status.MISSING ->
                InstallAssessment(InstallHealth.MISSING, "No game files found", location)
            M23InstallationDiscovery.Status.INACCESSIBLE,
            M23InstallationDiscovery.Status.UNSAFE_LINK ->
                InstallAssessment(InstallHealth.INACCESSIBLE, "Directory is inaccessible, linked, or exceeds safe scan bounds", location)
            M23InstallationDiscovery.Status.PARTIAL,
            M23InstallationDiscovery.Status.RECOVERY_REVIEW,
            M23InstallationDiscovery.Status.CONFLICT ->
                InstallAssessment(InstallHealth.INCOMPLETE,
                    "Some required DLLs or Content assets are missing, staged, or unsafe; manual review required", location)
            M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED ->
                InstallAssessment(InstallHealth.STRUCTURALLY_VALID,
                    "Core DLLs and Content present; Steam manifest hash verification not performed", location)
        }
    }

    fun smapi(folder: File = File(CinderboxPaths.SMAPI_DIR)): InstallAssessment {
        val observed = M23InstallationDiscovery.smapi(folder)
        return when (observed.status) {
            M23InstallationDiscovery.Status.MISSING ->
                InstallAssessment(InstallHealth.MISSING, "SMAPI directory not found", folder.absolutePath)
            M23InstallationDiscovery.Status.INACCESSIBLE,
            M23InstallationDiscovery.Status.UNSAFE_LINK ->
                InstallAssessment(InstallHealth.INACCESSIBLE, "SMAPI is inaccessible or unsafe", folder.absolutePath)
            M23InstallationDiscovery.Status.CANDIDATE_UNVERIFIED ->
                InstallAssessment(InstallHealth.DETECTED,
                    "SMAPI binary detected; runtime/version compatibility not verified", folder.absolutePath)
            else -> InstallAssessment(InstallHealth.INCOMPLETE,
                "SMAPI files or transaction are incomplete; manual review required", folder.absolutePath)
        }
    }

    fun scan(selectedGameDir: File, cinderboxInstalled: Boolean): InstallationSnapshot =
        scan(selectedGameDir, cinderboxInstalled, File(CinderboxPaths.ROOT_DIR))

    /** No write probe, even when the installation-health screen refreshes. */
    fun scan(selectedGameDir: File, cinderboxInstalled: Boolean, installationRoot: File,
             appVisibilityKnown: Boolean = true): InstallationSnapshot =
        InstallationSnapshot(
            selectedGame = game(selectedGameDir),
            cinderboxGame = game(File(installationRoot, "desktop/GameFiles")),
            smapi = smapi(File(installationRoot, "smapi-internal")),
            cinderboxApp = InstallAssessment(
                if (!appVisibilityKnown) InstallHealth.INACCESSIBLE
                else if (cinderboxInstalled) InstallHealth.DETECTED else InstallHealth.MISSING,
                if (!appVisibilityKnown) "Package visibility denied; installed state unknown"
                else if (cinderboxInstalled) "Cinderbox Android package detected; launch compatibility not verified"
                else "Cinderbox Android package not installed", "com.game.cinderbox"),
            storage = StorageCheck(false, "Read-only discovery; write access not tested. " +
                "Run destination preflight only when explicitly starting an operation."),
            discovery = M23InstallationDiscovery.inspect(selectedGameDir, installationRoot)
        )

}
