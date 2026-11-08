package com.sdvsync.mods.api

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast

/** Opens a verified Cinderbox handoff in a Firefox browser when available. */
object NexusBrowserLauncher {
    private val firefoxPackages = listOf(
        "org.mozilla.firefox", "org.mozilla.firefox_beta", "org.mozilla.fennec_fdroid"
    )

    fun open(context: Context, url: String) {
        // Only our HTTPS, exact-file bridge URLs may use this launcher.
        val uri = Uri.parse(url)
        if (uri.scheme != "https" || uri.host != "www.nexusmods.com" ||
            uri.getQueryParameter("cinderbox_mode") != "nxm" ||
            uri.getQueryParameter("cinderbox_file").isNullOrBlank()) return
        for (packageName in firefoxPackages) {
            try {
                context.startActivity(Intent(Intent.ACTION_VIEW, uri).apply {
                    `package` = packageName
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
                return
            } catch (_: ActivityNotFoundException) {
                // Continue to other Firefox distributions.
            } catch (_: SecurityException) {
                // Browser not permitted; try another option.
            }
        }
        Toast.makeText(context,
            "Firefox with Stardew Nexus Download Queue is needed for automatic handoff; opening Nexus normally.",
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
}
