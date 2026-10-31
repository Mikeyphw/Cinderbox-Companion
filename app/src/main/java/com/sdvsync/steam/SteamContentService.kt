package com.sdvsync.steam

import com.sdvsync.logging.AppLogger
import com.sdvsync.download.M24DepotManifestIdentity
import `in`.dragonbra.javasteam.steam.handlers.steamapps.PICSRequest
import `in`.dragonbra.javasteam.steam.handlers.steamapps.callback.PICSProductInfoCallback
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.future.await
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout

class SteamContentService(private val clientManager: SteamClientManager) {
    companion object {
        private const val TAG = "SteamContent"
        const val STARDEW_APP_ID = 413150
    }

    data class BranchInfo(val name: String, val buildId: Long, val passwordRequired: Boolean,
                          val timeUpdated: Long, val manifestFingerprint: String? = null,
                          val depotCount: Int = 0, val depotManifestIds: Map<Int, String> = emptyMap(),
                          val sharedDepotFromApps: Map<Int, Int> = emptyMap())

    data class AppContentInfo(val branches: List<BranchInfo>)

    suspend fun getAppBranches(): AppContentInfo = withContext(Dispatchers.IO) {
        val steamApps = clientManager.apps

        // 1. Get PICS access token for the app
        AppLogger.d(TAG, "Requesting PICS access token for AppID $STARDEW_APP_ID...")
        val tokensResult = steamApps.picsGetAccessTokens(app = STARDEW_APP_ID).await()
        val accessToken = tokensResult.appTokens[STARDEW_APP_ID] ?: 0L

        if (accessToken == 0L && tokensResult.appTokensDenied.contains(STARDEW_APP_ID)) {
            AppLogger.w(TAG, "Access token denied for AppID $STARDEW_APP_ID")
        }

        AppLogger.d(TAG, "Got PICS access token (len=${accessToken.toString().length})")

        // 2. Get product info using callback subscription (AsyncJobMultiple)
        val deferred = CompletableDeferred<PICSProductInfoCallback>()
        val sub = clientManager.callbackMgr.subscribe(PICSProductInfoCallback::class.java) { callback ->
            if (callback.apps.containsKey(STARDEW_APP_ID) || callback.unknownApps.contains(STARDEW_APP_ID)) {
                deferred.complete(callback)
            }
        }

        steamApps.picsGetProductInfo(
            app = PICSRequest(STARDEW_APP_ID, accessToken)
        )

        val productInfo = try {
            withTimeout(15_000) { deferred.await() }
        } finally {
            sub.close()
        }

        val appInfo = productInfo.apps[STARDEW_APP_ID]
        if (appInfo == null) {
            AppLogger.w(TAG, "No product info returned for AppID $STARDEW_APP_ID")
            return@withContext AppContentInfo(branches = emptyList())
        }

        // 3. Parse branches from KeyValue tree
        // Structure: appinfo -> depots -> branches -> <branchName> -> { buildid, timeupdated, pwdrequired }
        val depots = appInfo.keyValues["depots"]
        val branchesKv = depots["branches"]

        val branches = branchesKv.children.mapNotNull { branchKv ->
            val name = branchKv.name ?: return@mapNotNull null
            val buildId = branchKv["buildid"].asLong()
            val timeUpdated = branchKv["timeupdated"].asLong()
            val pwdRequired = branchKv["pwdrequired"].asBoolean()

            AppLogger.d(TAG, "Branch '$name': buildId=$buildId, timeUpdated=$timeUpdated, pwdRequired=$pwdRequired")

            // Every depot manifest identity comes from this same live PICS response.
            // Missing/ambiguous data is fail-closed for M24 live transfer; PICS
            // manifest references are NOT per-file signed manifest verification.
            val manifestIds = depots.children.mapNotNull directDepot@ { depot ->
                val id = depot.name?.toIntOrNull()?.takeIf { it > 0 } ?: return@directDepot null
                val gid = depot["manifests"][name]["gid"].asLong()
                if (gid <= 0L) null else id to gid.toString()
            }.toMap()
            val numericDepots = depots.children.mapNotNull { child ->
                child.name?.toIntOrNull()?.takeIf { it > 0 }
            }.toSortedSet()
            if (name == "public") {
                // IDs are non-secret; never log gid, account, token, password or raw PICS records.
                AppLogger.i(TAG, "M24 PICS public numeric depot IDs=${numericDepots.joinToString(",")}; " +
                    "manifest-bound IDs=${manifestIds.keys.sorted().joinToString(",")}; " +
                    "IDs lacking direct public gid=${(numericDepots - manifestIds.keys).joinToString(",")}")
            }
            // Missing direct GIDs may be *shared depots*. JavaSteam follows
            // depotfromapp when downloading; bind their GIDs from that parent
            // application's live PICS response, never from a local .sha file.
            val sharedSources = depots.children.mapNotNull sharedDepot@ { depot ->
                val id = depot.name?.toIntOrNull()?.takeIf { it > 0 } ?: return@sharedDepot null
                if (id in manifestIds) return@sharedDepot null
                val parent = depot["depotfromapp"].asLong()
                if (parent <= 0L || parent > Int.MAX_VALUE || parent == STARDEW_APP_ID.toLong())
                    null else id to parent.toInt()
            }.toMap()
            val snapshot = runCatching {
                M24DepotManifestIdentity.snapshot(name, buildId, manifestIds)
            }.getOrNull()
            BranchInfo(
                name = name,
                buildId = buildId,
                passwordRequired = pwdRequired,
                timeUpdated = timeUpdated,
                manifestFingerprint = snapshot?.fingerprint,
                depotCount = snapshot?.depotCount ?: 0,
                depotManifestIds = if (snapshot != null) manifestIds else emptyMap(),
                sharedDepotFromApps = if (snapshot != null) sharedSources else emptyMap()
            )
        }.sortedWith(compareByDescending<BranchInfo> { it.name == "public" }.thenByDescending { it.timeUpdated })

        AppLogger.d(TAG, "Found ${branches.size} branches for AppID $STARDEW_APP_ID")
        AppContentInfo(branches = branches)
    }

    /** Resolve only parent app/depot pairs advertised by Stardew's fresh PICS metadata.
     * A Steam-owned shared depot (e.g. Windows redistributable) must never be
     * approved using a local cached manifest ID or the SDK's callback alone.
     * All failures remain fatal to promotion; no unauthenticated fallback.
     */
    suspend fun resolveSharedDepotManifests(
        branch: String, sharedSources: Map<Int, Int>
    ): Map<Int, String> = withContext(Dispatchers.IO) {
        require(sharedSources.size <= 128 && sharedSources.keys.all { it > 0 } &&
            sharedSources.values.all { it > 0 && it != STARDEW_APP_ID }) {
            "Invalid shared Steam depot sources"
        }
        if (sharedSources.isEmpty()) return@withContext emptyMap()
        val result = linkedMapOf<Int, String>()
        val steamApps = clientManager.apps
        for ((parentId, depots) in sharedSources.entries.groupBy({ it.value }, { it.key })) {
            val tokenResult = steamApps.picsGetAccessTokens(app = parentId).await()
            val token = tokenResult.appTokens[parentId] ?: 0L
            check(parentId !in tokenResult.appTokensDenied) {
                "Shared depot parent PICS access denied"
            }
            val deferred = CompletableDeferred<PICSProductInfoCallback>()
            val sub = clientManager.callbackMgr.subscribe(PICSProductInfoCallback::class.java) { cb ->
                if (cb.apps.containsKey(parentId) || cb.unknownApps.contains(parentId)) deferred.complete(cb)
            }
            val payload = try {
                steamApps.picsGetProductInfo(app = PICSRequest(parentId, token))
                withTimeout(15_000) { deferred.await() }
            } finally {
                sub.close()
            }
            val appInfo = payload.apps[parentId]
                ?: error("Shared depot parent PICS metadata missing")
            val parentDepots = appInfo.keyValues["depots"]
            for (depotId in depots.sorted()) {
                val depot = parentDepots[depotId.toString()]
                var gid = depot["manifests"][branch]["gid"].asLong()
                // JavaSteam 1.8.0 resolves missing non-public branches to public.
                if (gid <= 0L && branch != "public") {
                    gid = depot["manifests"]["public"]["gid"].asLong()
                }
                check(gid > 0L) { "Shared depot $depotId has no parent PICS manifest ID" }
                result[depotId] = gid.toString()
            }
        }
        result.toMap()
    }
}
