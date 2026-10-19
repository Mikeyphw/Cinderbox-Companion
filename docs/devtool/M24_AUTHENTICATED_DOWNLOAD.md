# M24 — Steam selection, recovery identity and local hash safety (source phase)

**Base:** postmerge M23 `master` `66b491e553db1adb27ad7be89049d462560b0ca3` / CI `39089587138` SUCCESS.

## Implemented (source-bound; not live qualified)

- Existing Cinderbox is the main game app. M24 downloads remain opt-in to a **separate empty directory** using M23 protection; no automatic transfer to the imported Cinderbox game, saves, mods or SMAPI.
- UI requires live Steam login, fresh PICS branch with positive build ID, enabled verification, an independent destination and a required explicit positive size estimate plus storage budget and write preflight. Storage estimates are *not* Steam depot sizes and do not guarantee sufficient space. Stale UI branch metadata **alone cannot authorize the service**.
- App-private interrupted download checkpoint now can bind its owned session to a positive PICS branch build ID. The binding is committed atomically and checked before resume and in the foreground service. Old M6/M14–M23 fixture methods still work, but unbound/legacy checkpoints cannot authorize an M24 service transfer. Interruption keeps partial bytes, never auto-deletes them.
- Service rechecks current live Steam session + PICS branch build before starting and after DepotDownloader completion. Branch drift, missing PICS metadata, lost login and failed SDK callbacks block local completion; the checkpoint remains for inspection. A nonempty license list is **not proof of Stardew ownership**; actual depot authorization is a server-side step, not established by this source gate.
- Local SHA-256 file consistency scan is compulsory before clearing recovery. The success screen explicitly says **LOCAL_SHA256_ONLY_MANIFEST_UNATTESTED**, not authenticated Steam depot manifest. No account IDs, passwords or tokens are recorded in new checkpoint metadata or CI reports.
- `m24-check` and `m24-full` wrapper shortcuts reuse existing Devtool DAG jobs, and both GitHub Actions workflows produce per-commit source-bound JSON. The Android test APK gets four *new*, app-private synthetic cases; no earlier M14–M23 device suites are replayed.

## Critical open gates

**M24 is not fully qualified.** Live licensed Steam depot ownership; authenticated per-depot manifest/chunk proof; a trusted depot manifest-to-files comparison; atomic game directory commit; real network interruption/cancellation/reconnection; storage revocation/shortage and consented real download are **NOT_RUN**, and source or synthetic test PASS cannot substitute for them. `verifyAndRecord` only records self-computed local hashes. The existing downloader writes in place to its owned separate destination and is not an atomic game-directory transaction; do not claim it is.

The previous M23 10/10 and 3/3 Android receipts retain their original source attribution. The new M24 synthetic lane must be run using exact matching CI APK and test APK; its runner deliberately reports `installed_source_verified=false` until separately attested. Publishing and release signing remain disabled.

## M24 staged transfer increment (PR #34 follow-up)

- Live M24 transfers use a **separate, owned sibling staging directory**, not the selected final game path. The final path must be absent; even an empty preexisting directory is not replaced. Users may need to choose a new path.
- A durable app-private journal binds stage identity, destination, branch and build ID. Resumption after a process death only accepts the matching token and existing stage. Legacy direct-write sessions are rejected for *new* M24 transfers but their bytes are preserved.
- After local SHA-256 checks and another live PICS check, a same-filesystem `ATOMIC_MOVE` publishes the stage; no non-atomic copy fallback. If interrupted between rename and journal cleanup, cold recovery reconciles a matching marker and verifies the destination before clearing recovery.
- An explicit discard forgets ownership metadata without deleting partial files; it does not automatically clean orphaned stages.
- This is **local-only integrity**, NOT authenticated Steam file-manifest or entitlement evidence. `LOCAL_SHA256_ONLY_MANIFEST_UNATTESTED` remains the user-visible completion scope. Live Steam, manifest integrity and a physical device crash experiment remain unqualified. New device fixtures do not touch user game storage.
- Known limitation: concurrent unrelated external actors modifying the destination parent are not a qualified adversarial filesystem environment. Future manifest binding and destructive operation approval remain outstanding. Release publication disabled.


## M24 provenance and real-substrate inspection increment (PR #34)

- `scripts/devtool/m24_real_substrate.py` performs a **read-only installed APK pair byte attestation** after the user has installed the matching `debug-apk` and `m14-androidtest-apk` from GitHub Actions. It explicitly requires a run ID, exact commit and ADB serial. It checks the GitHub Actions run identity/status/branch, downloads those two run artifacts via the user's `gh` authorization, hashes the APK bytes, and compares them with `sha256sum` of both installed `pm path` APKs. Multiple split APKs, missing tools, different bytes and missing CI provenance fail closed. Both ADB transports may refer to the same device and are never counted as independent physical devices.
- The same probe observes only the existence of the known public Cinderbox game/SMAPI/legacy directory locations and the main `com.game.cinderbox` package; no file content, user accounts, saves or mods are read or enumerated. The positive receipt `PASS_CI_INSTALLED_APK_PAIR_BYTE_MATCH_READ_ONLY` attests **APK bytes only**. Missing Cinderbox visibility is a separate observation, not a forced install or a proof of integrity.
- `m24-provenance-check` runs pure host synthetic negative checks and a per-commit source/CI gate. CI emits its own source-bound JSON artifact. It intentionally does not run ADB or download APKs in CI.
- **Unmet:** the current JavaSteam integration provides PICS branch/build identity but no independently authenticated *depot-file manifest* or successful file-to-trusted-manifest comparison. A local SHA-256 ledger, presence of the Cinderbox game or a matched CI APK pair do not prove Steam ownership or depots. Real licensed, consented transfer and interruption/reconnection also remain NOT_RUN. No release publication or automatic mutation.


## M24 PICS depot-manifest identity binding (current increment)

- Parses positive numeric depot manifest GIDs from the selected branch's live PICS appinfo response, sorted and SHA-256 fingerprinted with app 413150, branch and build ID. A missing/invalid manifest set refuses a new live transfer. This metadata is an **identity pointer only**, not an independently authenticated per-file depot manifest.
- A newly started owned M24 stage stores the fresh depot-manifest fingerprint atomically in the private recovery journal after existing ownership/build checks. A restarted session, branch drift or manifest identity drift fails closed while preserving partial bytes. Existing historical fixtures remain compatible but cannot bypass the live service's fingerprint requirement.
- Steam entitlement, signed file manifests, chunk-to-file digest matching and a real consented Steam transfer remain **NOT_QUALIFIED**. Do not claim that this PICS identity fingerprint verifies game files or proves ownership. The final integrity scope remains `LOCAL_SHA256_ONLY_MANIFEST_UNATTESTED`.


## M24 depot cached-manifest file cross-check (follow-on candidate)

Before atomic promotion, the Steam downloader's cached `.DepotDownloader/<depot>_<manifest>.manifest`
files (and their SDK-generated `.sha` consistency checks) must correspond to live
PICS depot manifest IDs for SDK-reported completed depots. PICS may list unrelated
platform/language depots that must not be required for a Windows-only transfer. Every staged file must match its manifest file size and SHA-1,
no extra game files or symlink paths may appear, and a post-rename reconciliation rechecks
again before recording completion. A missing manifest, failed digest, or changed manifest
identity blocks promotion and retains partial data. The source does not touch original
Cinderbox game, saves, mods or SMAPI locations.

**Trust boundary:** JavaSteam's `.manifest.sha` checks a local cached manifest's SHA-1 and is
not a Valve digital signature. PICS IDs and manifest `fileHash` values support content
cross-checking, **not an independently verified Steam signature, explicit entitlement proof,
or evidence of a licensed live transfer**. The result scope is
`PICS_BOUND_DEPOT_SHA1_UNSIGNED`. Product-release, real-transfer, and signed-manifest claims
remain disallowed until real-source and device receipts independently close them.

### M24 live depot handoff visibility (pending device retest)

The initial authorized real transfer was observed stuck in the UI at “Waiting for depot progress…”. This means `onDownloadStarted` fired but no chunk/file progress callback was received; it does not by itself prove a CDN or Steam entitlement failure. JavaSteam 1.8.0 reports manifest and file allocation stages through `onStatusUpdate`, previously logged but not displayed. The adapter now maps those messages only to safe constant UI labels, checks the SDK failure flag promptly, replaces blocking `awaitCompletion()` with a cancellable completion-future await, and emits `STEAM_DEPOT_FIRST_CONTENT_TIMEOUT` after 240 seconds without content or `STEAM_DEPOT_CONTENT_STALLED` after 300 seconds without transfer activity. Neither timeout deletes owned checkpoint or staged bytes. The actual cause of a particular device hang still needs sanitized live logs; this is not an authenticated Steam entitlement receipt or release qualification.

## M24 live Windows depot mismatch and progress clarity (2026-10-18)

On a user-authorized isolated real Steam transfer, Android reported nonzero bytes and
files but subsequently failed closed with `Completed depots are not PICS-bound`.
The observed Windows depot ID was `413151`. Do not suppress or bypass this gate:
M24 PICS enumeration and SDK-completed depot selection must be reconciled against
actual authenticated branch metadata before staging can be published.

Progress now distinguishes transfer bytes, last-reported rate and completed files
from an unavailable overall total. A zero/stale per-depot SDK percentage is no
longer displayed as authoritative zero-percent progress. Debug logs contain only
public numerical depot IDs (not access tokens, GIDs, paths, account IDs, or
passwords). A mismatch names the missing depot(s) and preserves the checkpoint.
This patch is diagnostic and UI remediation, NOT closure of live-transfer proof.
