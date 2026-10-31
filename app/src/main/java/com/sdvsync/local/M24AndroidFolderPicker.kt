package com.sdvsync.local

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Environment
import android.provider.DocumentsContract
import java.io.File
import java.nio.file.Files

/** Android document-tree selection for direct-File downloads.
 * SAF grants alone DO NOT make arbitrary content providers accessible to File APIs.
 * Accept only a primary-storage directory that our existing File pipeline can see.
 */
object M24AndroidFolderPicker {
    fun resolve(context: Context, uri: Uri): File {
        require(uri.scheme == "content" && uri.authority == "com.android.externalstorage.documents" &&
            DocumentsContract.isTreeUri(uri)) {
            "This provider cannot be used for direct-file downloads; choose internal storage"
        }
        val relative = M24FolderSelectionPolicy.primaryRelativePath(DocumentsContract.getTreeDocumentId(uri))
        val root = Environment.getExternalStorageDirectory().canonicalFile
        val raw = File(root, relative).absoluteFile
        var candidate: File? = raw
        while (candidate != null && candidate != root) {
            require(!Files.isSymbolicLink(candidate.toPath())) { "Refusing symbolic-link folder" }
            candidate = candidate.parentFile
        }
        val selected = raw.canonicalFile
        require(selected.toPath().startsWith(root.toPath()) && selected != root &&
            selected.isDirectory && selected.canRead()) { "Selected folder is not accessible to the downloader" }
        // Persist the user's URI grant; direct File access still requires normal
        // Android storage permissions, checked again at start of transfer.
        context.contentResolver.takePersistableUriPermission(uri,
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        return selected
    }
}
