import com.sdvsync.local.M24FolderSelectionPolicy

fun main() {
    fun rejected(s: String) {
        try { M24FolderSelectionPolicy.primaryRelativePath(s) }
        catch (_: IllegalArgumentException) { return }
        error("Unsafe folder ID accepted")
    }
    check(M24FolderSelectionPolicy.primaryRelativePath("primary:Download/M24-Test") == "Download/M24-Test")
    for (value in listOf("primary:", "primary:.", "primary:../Game", "primary:Download/../Game",
        "primary:Download//Game", "primary:Download/./Game", "other:Download/Game", "primary:Download/:bad")) rejected(value)
    println("PASS_M24_ANDROID_FOLDER_POLICY_NEGATIVES")
}
