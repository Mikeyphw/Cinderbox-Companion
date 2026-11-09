package com.sdvsync.mods

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow

/** User preference affects confirmation only, never archive validation or recovery safeguards. */
object ModDownloadPreferences {
    private const val PREFS = "cinderbox_mod_downloads_v2"
    private const val APPROVAL = "require_install_approval"
    val revision = MutableStateFlow(0L)

    fun requiresApproval(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(APPROVAL, false)

    fun setRequiresApproval(context: Context, enabled: Boolean) {
        check(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(APPROVAL, enabled).commit()) { "Could not save approval preference" }
        revision.value = revision.value + 1L
    }
}
