package com.sdvsync.mods.api

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import com.sdvsync.BuildConfig
import com.sdvsync.mods.NexusLab03CPolicy

/** Opens an exact-file Cinderbox handoff in Iceraven or another supported Gecko browser. */
object NexusBrowserLauncher {
    internal val compatibleBrowserPackages = listOf(
        "io.github.forkmaintainers.iceraven",
        "org.mozilla.firefox", "org.mozilla.firefox_beta", "org.mozilla.fennec_fdroid"
    )

    fun open(context: Context, url: String) {
        // Only our HTTPS, exact-file bridge URLs may use this launcher.
        val uri = Uri.parse(url)
        if (uri.scheme != "https" || uri.host != "www.nexusmods.com" ||
            uri.getQueryParameter("cinderbox_mode") != "nxm" ||
            uri.getQueryParameter("cinderbox_file").isNullOrBlank()) return
        for (packageName in compatibleBrowserPackages) {
            try {
                context.startActivity(Intent(Intent.ACTION_VIEW, uri).apply {
                    `package` = packageName
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
                return
            } catch (_: ActivityNotFoundException) {
                // Continue to other supported Gecko distributions.
            } catch (_: SecurityException) {
                // Browser not permitted; try another option.
            }
        }
        Toast.makeText(context,
            "Iceraven or Firefox with Stardew Nexus Download Queue is needed for automatic handoff; opening Nexus normally.",
            Toast.LENGTH_LONG).show()
        try {
            context.startActivity(Intent(Intent.ACTION_VIEW, uri).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(context, "No browser can open Nexus Mods", Toast.LENGTH_LONG).show()
        } catch (_: SecurityException) {
            Toast.makeText(context, "Browser launch was blocked", Toast.LENGTH_LONG).show()
        }
    }

    /** LAB-only: open a plain official files page; do NOT route via NXM or production manager. */
    fun openLabFilePage(context: Context, url: String): Boolean {
        if (!BuildConfig.CBNX_LAB || context.packageName != "com.sdvsync.cbnx06lab") return false
        val uri = Uri.parse(url)
        val segments = uri.pathSegments
        if (segments.size != 3 || segments[0] != "stardewvalley" || segments[1] != "mods")
            return false
        val modId = segments[2]
        val fileId = uri.getQueryParameter("file_id") ?: return false
        if (url != NexusLab03CPolicy.canonicalUrl(modId, fileId)) return false
        for (packageName in compatibleBrowserPackages) {
            try {
                context.startActivity(Intent(Intent.ACTION_VIEW, uri).apply {
                    `package` = packageName
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
                // Accepted launch request is not proof of page load, Nexus consent or download.
                return true
            } catch (_: ActivityNotFoundException) {
                // No silent default-browser or production-NXM fallback in LAB.
            } catch (_: SecurityException) {
                // No installed/authorized compatible browser; fail closed.
            }
        }
        return false
    }
}
