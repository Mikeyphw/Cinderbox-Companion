package com.sdvsync.download

/** M24 PICS metadata binding. This is NOT a license, depot-manifest signature or
 * Steam ownership proof: the authenticated depot backend still decides entitlement.
 */
object M24SteamSelectionPolicy {
    const val APP_ID = 413150
    enum class Verdict { SIGNED_OUT, BUILD_UNKNOWN, BRANCH_CHANGED, PICS_BOUND_ONLY }

    fun assess(authenticated: Boolean, expectedBuild: Long, observedBuild: Long?): Verdict = when {
        !authenticated -> Verdict.SIGNED_OUT
        expectedBuild <= 0L || observedBuild == null || observedBuild <= 0L -> Verdict.BUILD_UNKNOWN
        expectedBuild != observedBuild -> Verdict.BRANCH_CHANGED
        else -> Verdict.PICS_BOUND_ONLY
    }

    /** A PICS match alone NEVER establishes a licensed game, authorized depot or
     * signed manifest. These require live backend validation and separate evidence.
     */
    fun requireBound(authenticated: Boolean, expectedBuild: Long, observedBuild: Long?) {
        check(assess(authenticated, expectedBuild, observedBuild) == Verdict.PICS_BOUND_ONLY) {
            "Steam session unavailable or branch build changed; download remains recoverable"
        }
    }
}
