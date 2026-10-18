# Persistent Devtool / Cinderbox improvements ledger

This ledger is cumulative; append future Devtool gaps and campaign findings rather than leaving them only in chat. Scope: `Mikeyphw/Cinderbox-Companion` Devtool overlay and test automation. Historical milestones remain acknowledged; none of their device evidence is reexecuted here.

| ID | Evidence / affected projects | Recommended change and rationale | Status |
|---|---|---|---|
| DEV-M19-PATH-001 | M19 first Android 16 `seedInterruptedDownloadCheckpoint` failed; Android system aliases such as `/data/user/0` can be symlink ancestors. Affects Cinderbox Android fixture base and source-bound Devtool tests. | Use reusable canonical app-private test fixture manager; retain strict production symlink rejection. | Implemented in M20; 52/52 Android device campaign PASS |
| DEV-M19-DIAG-002 | M19 initial `INSTRUMENTATION_INCOMPLETE_OR_FAILED` omitted actionable causes. Affects Devtool automation and Cinderbox source-bound device evidence. | Classify exceptions using fixed allowlist and Kotlin test line only; prohibit raw stack/path/token serialization. | Implemented and Android-qualified in M20 (52/52) |
| DEV-M19-FIXTURE-003 | An early failed M19 run may have left an isolated test directory; source runner had no inventory. | Persist cryptographically bound test-only ownership markers, ID-only inspection, explicit single-fixture cleanup with strict content verification; never bulk-delete user data. | Implemented in M20; ownership tests passed (device inventory cleanup remains opt-in) |
| DEV-M20-CASE-004 | Serial two-case Android campaigns cause repeated CI/device install cycles and risk incomplete result reporting. | One 52-case, eight-lane manifest; CI compile once, individually executable lanes and one source/provenance-bound consolidation, strict per-case totals. | Implemented, 52/52 M20 Android PASS |
| DEV-M20-SERVICE-005 | Production `GameDownloadService` has `START_NOT_STICKY`, coroutine jobs and connection to Steam; authenticated downloader cannot be safely tested under signed-out real-device fixture. | Preserve distinction between debug synthetic real Android foreground-worker lifecycle and actual Steam service. Future separately consented live-network integration required before stronger claims. | Explicit limitation / future work |
| DEV-M20-MERGE-006 | Multiple lane reports can otherwise be accidentally combined across APKs or PRs. | Reject source/CI/APK/device mismatch, overlapping lanes, missing test cases and absent genuine process-stop evidence; never infer release qualification. | Implemented, M20 consolidated 52/52 PASS |


### M20-IR-01 — Instrumentation teardown is not a worker-liveness receipt
- **Evidence:** PR #25 first Android run, CI `38917076629`, source
  `db985f5b0e19011a53b8911a3376c22ec53c53ec`: lanes A and B and C01–C07
  passed; pre-force-stop `pidof com.sdvsync` returned empty. No force-stop ran.
- **Affected:** `scripts/devtool/m20_qualification.py`; debug-only
  `M20SyntheticWorkerService`; genuine process-death evidence gate.
- **Improvement:** Re-arm and verify the non-exported synthetic foreground
  worker after instrumentation teardown, require live `ServiceRecord` and stable
  app PID, mark host-side lifecycle failures explicitly FAILED_OR_BLOCKED, and
  block force-stop if verification fails. Never substitute an
  Activity launch alone for proof of a running worker.
- **Status:** Re-arm confirmed on Android 16; lane C 8/8 PASS in PR #25.

| DEV-M20-G-UI-008 | Android 16 run at PR #25 `326d1045`, CI `38923143537`: G03/G05 both failed, while G01/G02/G04 passed. Test clicked passive Settings heading `Operation center` rather than the long CTA already qualified in M17. | Reuse M17's scroll-to navigation CTA; wait for Compose idle and confirm destination rendered before refresh. Preserve source-bound G-only retest. | Fixed and verified: M20 G/H 10/10 PASS, final consolidated 52/52 PASS |
| DEV-M20-DIAG-009 | The same failed run incorrectly reported `source_line:364` for both G03/G05 because instrumentation diagnostics searched the entire multi-case output, not the case's status event. | Group AndroidJUnitRunner events by `INSTRUMENTATION_STATUS_CODE` and matching test ID, classify only that event; retain allowlisted category/line, never publish raw stacks/paths. | Fixed and host-tested; M20 G/H 10/10 PASS, final 52/52 PASS |

### M21 — Consolidated actual-workflow and release-readiness campaign

| ID | Concrete evidence / affected projects | Recommended action / outcome | Status |
|---|---|---|---|
| DEV-M21-AUTH-010 | M20's 52 fixture-based scenarios do not exercise an actual authenticated Steam account and cloud metadata service. `SteamClientManager`, `SteamSessionStore`, `SteamCloudService`, `SteamContentService` are affected. | Require opt-in, non-mutating live Steam connection, encrypted session presence, license callback and cloud metadata enumeration. No raw secrets or user file names in reports; absence is BLOCKED rather than PASS. | Implemented M21 source/tests, CI/device pending |
| DEV-M21-LOG-011 | `SteamCloudService` previously emitted private cloud filenames, path prefixes, machine names and even decoded save text excerpts to application diagnostic logs. | Replace raw-value logging with aggregate transfer sizes/counts. Never emit batch IDs, raw cloud paths or save content. | Source change implemented; Kotlin CI pending |
| DEV-M21-APK-012 | M16 pinned the CI debug signer only. Existing release `keystore.jks` is separate and not automatically provisioned/qualified. A debug APK must not be labeled release-ready. | Enforce separately signed APK, independent APK and release-certificate pins, actual CI debug-signer comparison, verified package identity, and non-debuggable manifest. No signing keys in overlay or publication. | Implemented M21 release audit; real signed release artifact pending |
| DEV-M21-REAL-013 | M20 synthetic installation fixtures did not prove the presence of the actual Cinderbox Android package or that Companion's app-private data survives an explicit APK replacement. | Read PackageManager for actual `com.game.cinderbox`; require explicit opt-in, preserve a nonce-owned test marker across same-signer replacement and clean only that marker after success. Missing actual package is BLOCKED, not synthetic PASS. | Implemented M21 Android lane, real-device pending |
| DEV-M21-BOUND-014 | Repeating 74 completed M14–M20 device cases for new acceptance would obscure remaining unqualified areas and require unnecessary test cycles. | Separate 18-case versioned M21 matrix, reusable M14/M16 provenance/signature checks, independently executable lanes, one PR/one CI debug build, strict source/CI/APK/device merging. | Implemented M21 host/tooling, CI pending |

| DEV-M21-COMPILE-015 | CI run `38940534401` at M21 PR #26 commit `ac0c0f7d3d61b5a16ae572ee06e8bfa7e15b35d2` failed `:app:compileDebugAndroidTestKotlin`: `M21ReadinessDeviceTest.kt:5:33 Unresolved reference assertExists`. The app/debug APK and all M21 host checks had passed, but the Android test APK did not compile. | Remove the invalid `androidx.compose.ui.test.assertExists` import (the API is a `SemanticsNodeInteraction` member), add a source-bound host regression guarding against reintroduction, require newly successful AndroidTest CI before device qualification. | Hotfix authored; new CI/device verification pending |


### M21 completion and provenance follow-up — 2026-10-16

| ID | Evidence / affected projects | Action | Status |
|---|---|---|---|
| DEV-M21-PR-HIST-016 | M21 acceptance lane R first failed `PR_MERGE_COMMIT_UNAVAILABLE`: GitHub PR #26 remained open but its live merge_commit_sha was null, while CI run 38946596038 provenance established synthetic checkout dc7439617acaa10823a5e9bc95091bf8771f21f2 with matching exact Git ref and two parents. | Recover only from the CI artifact's cryptographically anchored source checkout when live PR SHA is null; demand exact PR ref, current immutable ref and exact ordered parents; otherwise fail closed. | Source-bound fix and regression tests implemented for integration; historical recovery 18/18 PASS on original reviewed commit. |
| DEV-M21-SIGNER-017 | M21 lane R failed `M21_APK_SIGNER_AMBIGUOUS` despite GitHub Actions release candidate run 38964234525 verifying the APK/signature. `m21_campaign.py` depended on a single exact human-readable apksigner digest line. | Keep `apksigner verify` mandatory, then parse sole consistent v2/v3 signer certificate with existing `m3_apk_signing.certificate_sha256`; assert unchanged APK bytes before/after. Reject ambiguous, missing, changed or invalid signatures. | Source-bound fix and regression tests implemented for integration; independently pinned release candidate 18/18 PASS on historical acceptance. |
| DEV-M21-COMPLETE-018 | Signed release run 38964234525 SUCCESS; `cinderbox-m21-final.json` PASS_M21_PREPUBLICATION_ACCEPTANCE (U4 I6 T4 R4). 74 earlier Android cases were not reexecuted. | Preserve immutable final M21 evidence separately from integration changes; no automatic release publication or certification inferred. | 18/18 M21 acceptance PASS on tested commit d93d21d; integration and broader release qualification separate. |
### M21-CI-SDK-015 — Release verifier masked Android SDK tool discovery failures
- **Evidence:** `Mikeyphw/Cinderbox-Companion` release candidate GitHub Actions run
  `38960889421`, workflow commit `8a0d733a1553c57186907e8847010f559da737e6`;
  release keystore/certificate provisioning PASS, `:app:assembleRelease` PASS (53
  tasks), but verification emitted `M21_RELEASE_APK_SIGNATURE_INVALID`, hiding
  whether `apksigner` was absent or cryptographic verification actually failed.
- **Affected:** `scripts/devtool/m21_actions_release.py` and release candidate
  workflow; `android-actions/setup-android` does not promise pinned build-tools
  binaries are in PATH, while M16 already had SDK-directory fallback.
- **Improvement:** Resolve both `apksigner` and `aapt` from the explicitly
  installed `$ANDROID_HOME/build-tools/35.0.0/` (or `ANDROID_SDK_ROOT`);
  use PATH fallback only for local runs without an SDK root; report distinct
  fail-closed unavailable-tool errors without exposing credentials. Preserve
  real signature, independent release cert, package and debuggability checks.
  Add host regression coverage for pinned-tool selection and missing binaries.
- **Status:** Fix implemented and nine focused host tests PASS; new CI and a
  real signed APK verification required. The original failure cause is not
  definitively confirmed until the corrected verifier executes in Actions.

### UI-D01 — theme evidence gap (2026-10-17)

| ID | Evidence / affected projects | Recommendation | Status |
|---|---|---|---|
| DEV-UI-D01-001 | Existing M17 UI instrumentation asserts offline Settings/navigation and operation semantics, but provides no two-theme contrast or image baselines. Affects Cinderbox Companion and Devtool-driven GitHub Actions UI qualification. | Add source-bound UI contrast host checks now; build both APKs in GitHub CI; collect optional synthetic screenshots and 320dp/font-scale visual evidence in UI-D03. Keep screenshot and real-device gates explicitly NOT_RUN until executed. | Host source checks added in UI-D01; CI/device and screenshot gates pending |


### UI-D01 Devtool integration audit — 2026-10-17

| ID | Evidence / affected projects | Action | Status |
|---|---|---|---|
| DEV-UI-D01-019 | Original UI-D01 package used custom `apply.py` + SHA checker despite installed Devtool `apply-overlay` inventory, transaction, branch, rollback, validation, EXO and commit machinery. Affected: Cinderbox overlays and other adopters. | Replace with native schema-v2 `.devtool-artifact.json` containing SHA-256 preimages, validation script, atomic transactions, target binding and commit policy; remove parallel installer. | Implemented in replacement native UI-D01 overlay; runtime apply pending |
| DEV-UI-D01-020 | `.devtool.toml` has reusable `security-contract`, `unit-tests`, `android-lint`, `debug-apk`, `verify-debug-apk` jobs, but the initial UI patch only changed Actions workflow scripts. | Define one `earthy-source` target-local command job, `earthy-check`/`earthy-full` DAGs and wrapper shortcuts, with security dependency and existing Android jobs reused unchanged. | Implemented; runtime DAG validation pending |
| DEV-UI-D01-021 | UI-D01 was initially run through duplicate static+unittest snippets in both `.github/workflows/build.yml` and `devtool-android-build.yml`. | Put one fail-closed `ui_d01_gate.py` in source, call it from both workflows and Devtool job, emit SHA-256 exact-source JSON receipts with explicit unqualified status, upload receipts. Do not pull/install an unpinned Devtool version in CI. | Implemented; GitHub Actions unverified |
| DEV-UI-D01-022 | Host source validation has no Android compilation/device execution; static string checks cannot prove actual Compose behavior. | Continue existing GitHub debug signing, test, lint, assembly, AndroidTest APK creation; separately run explicit Android UI qualification against pinned CI source. Do not count M21 historical observations as UI-D01 passes. | Open — compilation and device tests pending |
| DEV-UI-D01-023 | Existing Devtool schema's `validation.script` can run host checks without Gradle using `validation.tasks=[]`. Android builds are expensive, especially on Termux. | Make native apply cheap: required script host gate, no Gradle; offer explicit `devtoolw earthy-full` as opt-in long chain and leave CI to build normal signed debug artifact once. | Implemented; runtime apply pending |

### UI-D02 — continuation from successful UI-D01 GitHub CI

| ID | Evidence / affected projects | Recommendation / design outcome | Status |
|---|---|---|---|
| DEV-UI-D02-01 | PR #29 head `156bd652` GitHub Actions `39004991945` succeeded, including D01 source gate and APK/instrumentation compilation; on-device contrast and dialogs not exercised | Reuse target-local `earthy-components-host` from `earthy-d02-check` and `earthy-d02-full` DAGs, with exact-file SHA256 receipt and CI artifact upload; don't fork Android build logic or claim device PASS from CI | Implemented, host check; Android CI and device pending |
| DEV-UI-D02-02 | Static Classic palettes in Steam badge, spinner, wizard, empty-state sprite and Save Viewer persisted despite D01 Earthy mode | Move colors into existing Compose `SdvSyncThemeExtras` / Material semantic schemes; preserve Classic branches, status meaning, and read-only operation | Implemented, synthetic tests planned |
| DEV-UI-D02-03 | Generic card and dialog surfaces and header did not fully match earthy palette | Style shared surfaces centrally with style-conditional appearance, no per-screen backend changes; assess narrow devices and accessibility in D03 | Implemented, device validation pending |

| DEV-OVERLAY-CONFLICT-UI-D02-04 | Native Devtool overlay preflight on **already-applied** UI-D02 artifact (2026-10-17) raised `NameError: name 'sha256_file' is not defined` at `devtool/overlay/conflicts.py:38` via `check_overlay -> detect_inventory_conflicts`. The **clean preimage** preflight passed with zero conflicts, and atomic application completed all six stages; the recheck alone errored. Affects Devtool overlay conflict reporting for changed existing files across repositories. | Import the existing `sha256_file` helper in `devtool/overlay/conflicts.py`; add a regression for rechecking modified-file source SHA256, checking applied twice, and intentionally modified preimage. Preserve fail-closed behavior and prefer typed conflict receipts over exceptions. | **Open Devtool core bug; recorded, not patched in Cinderbox** |

### UI-D03 — source-bound accessibility and screenshot evidence

| ID | Evidence / affected projects | Recommendation | Status |
|---|---|---|---|
| DEV-UI-D03-01 | UI-D02 confirmed CI success `39006846654`, but Cinderbox `StardewBottomBar.kt` used bare clickable columns without tab role/selected semantics and only 6dp vertical padding. Pixel progress bar was visual-only. | Add selectable tab semantics and 56dp minimum touch height, accessible progress range, and a readable spinner state. Use Android instrumentation for semantics and accessibility behavior. | Implemented in UI-D03 source; Android CI and device validation pending |
| DEV-UI-D03-02 | UI-D01 host checked eight hardcoded color pairs; device screenshot and font scaling were absent. Affects Cinderbox, Devtool workflow evidence and future Compose adopters. | Parse 16 functional WCAG contrast pairs directly from current Kotlin color schemes; add synthetic 320dp / 160% font tests and explicit opt-in, private-file screenshot export, with never-assumed APK attestation. | Implemented in UI-D03 source; CI, on-device screenshots and visual review pending |
| DEV-UI-D03-03 | UI-D02 stacked PR #30 base `feature/ui-d01-earthy-theme` did not trigger `Build Debug APK`: workflow `pull_request` only included main/master. Manual workflow_dispatch run `39006846654` was successful. | Retain source-bound manual Devtool dispatch for stacked PRs and add explicit workflow trigger for stacked branches only after reviewing CI load/security; document that a PR being open does not imply a CI run. | Logged; manual workflow dispatch available, broad PR trigger not changed |
| DEV-OVERLAY-CONFLICT-UI-D02-04 | Devtool rechecking a previously applied overlay throws undefined `sha256_file` instead of producing conflict classification. | Correct helper import/test in upstream Devtool; never amend Cinderbox copy of Devtool core. | Open upstream; unchanged |


### M22 — baseline and source-bound evidence consolidation (2026-10-17)

| ID | Evidence / affected projects | Recommendation / resolution | Status |
|---|---|---|---|
| DEV-M22-HIST-001 | The M21 handoff captures 74 M14–M20 and 18 M21 reported historical passes, but original on-device receipt files were **not included**. Affects Cinderbox M22 and any Devtool qualification consumer. | Keep a separate immutable-history reference contract, record original-source/run IDs and mark original receipt completeness `NOT_ATTACHED`; never transplant 92 passes onto latest `master`. Add strict count/status tampering tests and independent current-source binding. | **Implemented host source contract; original receipt collection remains outstanding** |
| DEV-M22-BASE-002 | Earthy PRs #29–31 were merged, final postmerge source `5ba587e2...`, GitHub Actions `39040952179` SUCCESS, leaving earlier M21 baseline in handoff stale for current UI source. | Inventory live new base SHA, retain M21 SHA/CI provenance unchanged, hash current Devtool/CI/policy/source inputs, machine-report new CI as not yet final verified. | **Implemented M22 read-only gate; new source GitHub CI pending** |
| DEV-M22-DAG-003 | Existing `.devtool.toml` already has reusable `security-contract`, `unit-tests`, `android-lint`, `debug-apk`, `verify-debug-apk`; adding separate scripts for each source action would duplicate work. | Add `m22-host-tests` + `m22-baseline` jobs and 3-node `m22-check` / 7-node `m22-full` target-local dependency DAGs; provide wrapper shortcuts, reusing existing Android jobs. | **Implemented; native Devtool runtime rehearsal pending** |
| DEV-M22-CI-004 | Stacked PR builds did not auto-trigger until retargeted, and postmerge runs are distinct from successful branch builds. Current evidence requires exact checkout/run/artifact binding. | Add one M22 host gate invoked identically by both existing Actions workflows, upload sanitized versioned JSON; reject incorrect `GITHUB_SHA`/repository, keep old CI results as historic anchors only. | **Implemented; CI execution of new source pending** |
| DEV-M22-ROADMAP-005 | M23/M24 source modules exist, but existence and historic synthetic tests do not prove actual installed game, SAF/root readiness, authorized Steam depot downloads, resumable real transfer or atomic game commit. | Version and freeze M22–M29 gap matrix; keep M23/M24 as NOT_RUN and seek separate user authorization for real-game/Steam operations. | **M22 inventory implemented; M23/M24 still open** |


### M23 — authoritative read-only installation discovery (2026-10-17)

| ID | Evidence / affected projects | Recommendation / implementation | Status |
|---|---|---|---|
| DEV-M23-001 | Existing `InstallationScanner.game()` returned `STRUCTURALLY_VALID` on core DLL names + Content alone, without signed depot manifest/version provenance. M23 could wrongly convey a verified, compatible complete game. | Introduce separate explicit `CANDIDATE_UNVERIFIED` finding with no authorization, version unknown, clear blockers; preserve legacy scanner compatibility while making new discovery authoritative for health and new download preflight. | Implemented in M23 source; Android CI/device pending |
| DEV-M23-002 | Previous `InstallationHealthScreen` indirectly called `StoragePreflight.check()` which creates and deletes a temporary probe file, contrary to non-mutating discovery intent. | Remove the write probe from read-only `InstallationScanner.scan()`; keep destination preflight exclusively at explicit operation start. | Implemented and synthetic test added; device pending |
| DEV-M23-003 | Old health UI did not show current 0.8+/legacy conflict, staged archives, recovery markers, SMAPI staged state, or evidence provenance separately. | Bounded direct File inventory, no recursive scan or symlink following, split statuses and read-only dashboard; block new downloads where any existing/partial installation is found, but preserve owned checkpoint resume. | Implemented; real provider/device proof pending |
| DEV-M23-004 | Android SAF grant, Shizuku service, root availability, or `MANAGE_EXTERNAL_STORAGE` flag alone does not attest to actual read access at a user-selected path. | Report `DIRECT_FILE_READ_ONLY_OBSERVATION_WRITE_NOT_TESTED` and explicitly avoid equating provider availability with readable bytes; introduce provider-backed read-only inventories separately in M27. | Open Android provider-qualified extension; not misrepresented as PASS |
| DEV-M23-005 | Prior M22/M21 evidence should not be overwritten or 'upgraded' by host source checks on new code. | Reuse existing native Devtool M22 source-bound job; add a single M23 host gate called identically by both CI workflows and one DAG; keep historical observations attached only to original provenance. | Implemented; new GitHub and device evidence pending |

### M23 — test APK adoption after source-only qualification

| ID | Evidence / affected projects | Recommendation / implementation | Status |
|---|---|---|---|
| DEV-M23-006 | PR #33 adds M23 production logic and app JVM tests, but preexisting Android test APK runs M14–M21 without a direct M23 class. Host source PASS and AndroidTest compilation are not on-device M23 qualification. | Reuse `com.sdvsync.test` by adding ten private-fixture M23 Android tests, the source-bound Devtool `m23-device-check` job/DAG, and CI validation; keep physical execution opt-in and unqualified until a real signed APK/device receipt. | Implemented test-source contract; Android CI and device pending |

### DEV-M23-RUNNER-EXACT-METHOD-01 — Fixed in M23 hotfix (Oct 17, 2026)
- **Evidence:** M23 Android instrumentation report had `m23_01`–`m23_10` all `NOT_COMPLETED` despite manually installed APKs; `m14_device_qualification.parse_instrumentation` expects complete `test=` values while the M23 wrapper passed only prefixes.
- **Affected:** Cinderbox M23; reusable Devtool/device-runner design.
- **Change:** Compare source-attested exact instrumentation method names and normalize only after parsing. Retain fail-closed outcomes and sanitized source-independent reports.
- **Status:** Code fixed; host parsing regressions added; real-device rerun pending. Consider reusable case-id normalization as a future Devtool capability.


### M23-CB-001 — Cinderbox-first discovery and download authorization (2026-10-17)

| ID | Concrete evidence / affected projects | Recommendation / change | Status |
|---|---|---|---|
| DEV-M23-CB-SCOPE-001 | PR #33 source `a044cffd63fefe4057cafee9c38e6817c20843a1`, `GameDownloadViewModel.startDownload` used `discovered.gameAlreadyPresent`, aggregating selected download destination with `/storage/emulated/0/StardewValley/desktop/GameFiles`. On the user's Android screenshots, selected `/Download/StardewValley` was MISSING, primary game STRUCTURALLY_VALID, `smapi-internal` DETECTED. A previous real APK synthetic suite passed 10/10 but did not cover this user workflow. | Introduce independent Cinderbox primary-game visibility and destination-only read-only gate; protect every main-tree subtree and all ancestors with segment-based canonical ancestry checks; retain Steam, capacity, write and checkpoint gates. Duplicate the guard in the download manager. | Source implementation and host tests; CI and new 3-case device tests pending |
| DEV-M23-CB-COPY-002 | `GameDownloadManager.copyToCinderbox` previously wrote source DLLs into existing `desktop/GameFiles` via `outputStream()` without first refusing imported Cinderbox files. | Refuse any nonempty/inaccessible primary game destination, reject overlapping sources and symlink paths; a future separately reviewed/backed-up repair may update the main installation. Preserve actual Cinderbox ZIP imports as data, not verified Steam depots. | Source guard added; Android compilation/device confirmation pending |
| DEV-M23-CB-READ-003 | `GameDownloadViewModel` called `StoragePreflight.check` during initial screen display and every read-only refresh; that helper creates a temporary file. | Keep passive UI inspection read-only; perform writable storage probe only upon explicit Start Download. No implicit use of SAF/Root/Shizuku as direct File permission. | Source adjusted; CI/device confirmation pending |
| DEV-M23-CB-EVID-004 | Ten M23 synthetic Android cases `PASS_10_SYNTHETIC_DEVICE_TESTS_UNBOUND` on earlier source, but their tests exercised path recognition not primary-vs-destination scoping. | Add a separate 3-case app-private Android test lane and exact-method-name runner. Never carry over earlier 10/10 as new-source qualification, and never infer real imported-game integrity from a synthetic test. | New lane authored; execution outstanding |
