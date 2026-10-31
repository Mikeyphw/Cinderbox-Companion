package com.sdvsync.local

/** Only primary shared-storage subdirectories can be mapped safely into
 * the existing direct-File downloader. Content-provider URIs are not paths.
 */
object M24FolderSelectionPolicy {
    fun primaryRelativePath(documentId: String): String {
        require(documentId.startsWith("primary:")) { "Choose internal shared storage" }
        val relative = documentId.removePrefix("primary:")
        require(relative.isNotEmpty() && relative.length <= 1024 &&
            relative.split('/').all { part -> part.isNotBlank() && part != "." &&
                part != ".." && !part.contains('\\') &&
                !part.contains('\u0000') && !part.contains(':') }) {
            "Choose a safe non-root download folder"
        }
        return relative
    }
}
