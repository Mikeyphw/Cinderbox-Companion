package com.sdvsync.local

import java.io.File
import java.nio.file.Files

/**
 * The original Cinderbox app owns its StardewValley tree. Discovery of that
 * tree is read-only and is NOT permission to download into, overwrite, or
 * repair it. A separate empty destination remains eligible for the usual
 * Steam, capacity, writable-storage, and checkpoint gates.
 */
object M23CinderboxFirstPolicy {
    enum class Code {
        EMPTY_SEPARATE_DESTINATION,
        PROTECTED_CINDERBOX_TREE,
        EXISTING_OR_PARTIAL_SELECTED_DESTINATION,
        DESTINATION_UNREADABLE,
        UNSAFE_OR_NONABSOLUTE_DESTINATION
    }

    data class Decision(val code: Code, val separateEmptyDestination: Boolean) {
        // This is only the read-only path gate, NEVER download authorization.
        val authorizesDownload: Boolean = false
    }

    private fun hasSymlinkAncestor(file: File): Boolean {
        var item: File? = file.absoluteFile
        while (item != null) {
            if (Files.isSymbolicLink(item.toPath())) return true
            item = item.parentFile
        }
        return false
    }

    /** No filesystem mutations, including no temporary permission probe. */
    fun assess(destination: File, cinderboxRoot: File): Decision {
        if (!destination.isAbsolute || !cinderboxRoot.isAbsolute ||
            hasSymlinkAncestor(destination) || hasSymlinkAncestor(cinderboxRoot)) {
            return Decision(Code.UNSAFE_OR_NONABSOLUTE_DESTINATION, false)
        }
        val target: File
        val primary: File
        try {
            target = destination.canonicalFile
            primary = cinderboxRoot.canonicalFile
        } catch (_: java.io.IOException) {
            return Decision(Code.UNSAFE_OR_NONABSOLUTE_DESTINATION, false)
        } catch (_: SecurityException) {
            return Decision(Code.UNSAFE_OR_NONABSOLUTE_DESTINATION, false)
        }
        // Both ancestors and descendants are prohibited: a download into the
        // parent of Cinderbox's root could collide with an existing install.
        if (target.toPath().startsWith(primary.toPath()) ||
            primary.toPath().startsWith(target.toPath())) {
            return Decision(Code.PROTECTED_CINDERBOX_TREE, false)
        }
        val selected = M23InstallationDiscovery.game(destination)
        return when (selected.status) {
            M23InstallationDiscovery.Status.MISSING ->
                Decision(Code.EMPTY_SEPARATE_DESTINATION, true)
            M23InstallationDiscovery.Status.INACCESSIBLE,
            M23InstallationDiscovery.Status.UNSAFE_LINK ->
                Decision(Code.DESTINATION_UNREADABLE, false)
            else -> Decision(Code.EXISTING_OR_PARTIAL_SELECTED_DESTINATION, false)
        }
    }
}
