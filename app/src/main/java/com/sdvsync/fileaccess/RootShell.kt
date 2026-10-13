package com.sdvsync.fileaccess

/** Quote one POSIX shell argument; never interpolate an unquoted filesystem path. */
internal object RootShell {
    fun quote(value: String): String = "'" + value.replace("'", "'\\''") + "'"
}
