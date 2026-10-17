package com.sdvsync.ui.theme

import android.content.Context
import androidx.datastore.core.handlers.ReplaceFileCorruptionHandler
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map

/** All appearance data stays in a dedicated, app-private store: no Steam or save dependencies. */
enum class AppearanceStyle { CLASSIC, EARTHY }
enum class AppearanceMode { SYSTEM, LIGHT, DARK;
    fun resolve(systemDark: Boolean): Boolean = when (this) {
        SYSTEM -> systemDark
        LIGHT -> false
        DARK -> true
    }
}

data class AppearanceSettings(
    val style: AppearanceStyle = AppearanceStyle.CLASSIC,
    val mode: AppearanceMode = AppearanceMode.SYSTEM
)

private const val STORE_NAME = "cinderbox_appearance"
private val Context.appearanceDataStore by preferencesDataStore(
    name = STORE_NAME,
    corruptionHandler = ReplaceFileCorruptionHandler(produceNewData = { emptyPreferences() })
)

/** Unknown persisted values fail safely back to Classic/system, including on downgrade. */
fun parseAppearanceStyle(value: String?): AppearanceStyle =
    AppearanceStyle.entries.firstOrNull { it.name == value } ?: AppearanceStyle.CLASSIC

fun parseAppearanceMode(value: String?): AppearanceMode =
    AppearanceMode.entries.firstOrNull { it.name == value } ?: AppearanceMode.SYSTEM

class AppearancePreferences(context: Context) {
    private val store = context.applicationContext.appearanceDataStore

    val settings: Flow<AppearanceSettings> = store.data
        .catch { cause ->
            if (cause is IOException) emit(emptyPreferences()) else throw cause
        }
        .map { preferences: Preferences ->
            AppearanceSettings(
                style = parseAppearanceStyle(preferences[STYLE]),
                mode = parseAppearanceMode(preferences[MODE])
            )
        }

    suspend fun setStyle(style: AppearanceStyle) {
        store.edit { it[STYLE] = style.name }
    }

    suspend fun setMode(mode: AppearanceMode) {
        store.edit { it[MODE] = mode.name }
    }

    private companion object {
        val STYLE = stringPreferencesKey("style")
        val MODE = stringPreferencesKey("mode")
    }
}
