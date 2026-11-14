package com.sdvsync.cinderbox

object CinderboxPaths {
    val ROOT_DIR: String get() = CinderboxLabBoundary.root()
    val DESKTOP_DIR: String get() = "$ROOT_DIR/desktop"

    val GAME_FILES_DIR: String get() = "$DESKTOP_DIR/GameFiles"
    val SAVES_DIR: String get() = "$DESKTOP_DIR/Saves"
    val MODS_DIR: String get() = "$DESKTOP_DIR/Mods"
    val SMAPI_DIR: String get() = "$ROOT_DIR/smapi-internal"

    val LEGACY_GAME_FILES_DIR: String get() = "$ROOT_DIR/GameFiles"
    val LEGACY_SAVES_DIR: String get() = "$ROOT_DIR/Saves"
    val LEGACY_MODS_DIR: String get() = "$ROOT_DIR/Mods"

    fun isInstalled(): Boolean = CinderboxLayout().isInstalled()
}
