# M23: Read-only installation evidence and download guard

## Implementation

M23 builds on merged M22 `master` commit `3d0454574d49f74eb0e8407d2d266b3d9e49d96a` (postmerge run `39044683862` SUCCESS). The source-pinned native Devtool artifact adds an explicitly bounded `M23InstallationDiscovery` component and integrates its observations into the existing Installation Health screen and the existing GameDownloadViewModel consent gate.

- Explicit user-selected folder plus `StardewValley/desktop/GameFiles` (0.8+) and `StardewValley/GameFiles` (legacy) are independently inspected. Separate, known `smapi-internal` state, partial archives, download marker, recovery stage, and conflicting layouts are recorded; no automatic migration is performed.
- Enumerates at most 256 immediate entries at any inspected directory. Only the known `Content` level is inspected, never a recursive install scan. Rejects every symlink or inaccessible/oversized listing. Reads existing file metadata only, without opening user content and without following links.
- `CANDIDATE_UNVERIFIED` is **not** a healthy/complete/compatible installation. Without an authenticated Steam depot manifest and version attestation, `verified=false`, `canInstallOrOverwrite=false`, version unknown, and download authorizations remain false. SMAPI presence alone cannot prove compatibility.
- Folder paths use direct `File` access only. SAF URI grants, Root, Shizuku and manual import availability are not interchangeable with direct filesystem permissions. Missing/inaccessible results mean the selected provider cannot read, not that data is absent. An explicit provider-backed read-only scanner is outstanding for M27.
- Read-only Installation Health no longer invokes `StoragePreflight.check()`, which creates a temporary write probe. Existing explicit, user-requested write workflows continue to use their preflight. The discovery dashboard labels write access *not tested*, never writable.
- New download attempts are blocked when an existing current, legacy, selected, partial or unknown recovery path is detected. A matching, owned interrupted checkpoint can still resume through existing recovery validation. The actual download manager retains its existing guard independently.
- Cinderbox `com.game.cinderbox` package recognition is retained through Android PackageManager; no launch/version/certificate equivalence is inferred from mere presence.

## Qualification

`./devtoolw m23-check` executes security -> M22 baseline -> M23 host tests -> M23 source inventory, using existing Devtool DAGs and evidence. `./devtoolw m23-full` reuses unit tests, lint, signed debug APK and APK verification. GitHub Actions both execute the identical `m23_discovery_gate.py`, uploading JSON bound to the exact commit SHA. JUnit fixture tests cover complete-looking but unverified game, dual layout conflict, partial archives, interrupted downloads/SMAPI, symlink rejection, bounded directory inventory, and no write probe.

**M23 host PASS is NOT device qualification.** A consented read-only Android check must still test the real installed Cinderbox package, storage routes/revocation and the actual selected folder. The original M14–M21 device-local receipts remain unattached; historical observations are not rerun or replaced. M24 Steam transfer/manifest proof, M25 mods, M26 cloud, M27 access-provider qualification, M28 signing and M29 publication remain separate milestones. Automatic installation and release publication stay disabled.

## Next evidence

1. Validate the precise M23 source SHA through GitHub Actions: Android compilation, unit tests and instrumentation APK compilation.
2. Review read-only Health dashboard on a device with consented test directories, including legacy/modern conflict, inaccessible access path and SMAPI stage.
3. Record APK signer and source provenance separately; do not claim `M23_DEVICE_PASS` solely because the debug APK installs.

## M23 Android synthetic instrumentation qualification extension

PR #33 includes production M23 source and existing JUnit host tests. The existing
`com.sdvsync.test` instrumentation APK originally contained M14–M21, not M23.
This additive qualification patch introduces
`M23DiscoveryDeviceTest` with **10 app-private synthetic Android cases**:
missing-path refusal, modern candidate not verified, legacy/modern collision,
staging review, untrusted archive, SMAPI recovery, symlink refusal, enumeration
bound, absence of write probes, and selected archive-wrapper handling.
The fixtures are disposable and owned under `com.sdvsync` private cache. They are
**not** actual game directories, and the test does not access Steam credentials,
real saves, external storage, SAF, Root or Shizuku.

`./devtoolw m23-device-check` is a source-only DAG, not a claim of execution.
Both existing CI jobs run the same gate and compile the instrumentation APK.
After exact-source CI succeeds, on-device `am instrument` must actually run this
class and emit 10/10 PASS plus a sanitized device receipt. The user must opt in
to any debug APK replacement; never uninstall, clear data or override mismatched
signatures just to run a test. Real selected-file/SAF permission qualification
remains a separate, authorized activity. No prior M14–M22 results are overwritten.

After exact-source CI and explicit installation of matching signed debug APKs,
run **only** the M23 test class from the existing test app:

```sh
python3 scripts/devtool/m23_device_run.py \
  --execute-synthetic-tests --ci-run-id <SUCCESSFUL_CI_RUN_ID> \
  --output "$HOME/cinderbox-m23-device.json"
```

`--ci-run-id` is a *label*, not APK attestation. Until installed package
source/signature provenance is separately verified, the best possible result
is `PASS_10_SYNTHETIC_DEVICE_TESTS_UNBOUND`, with `device_qualified=false`.
The runner does **not** install APKs, perform authentic game discovery,
request permissions or clear any app state.

## M23 test-runner diagnosis and repair (Oct 17, 2026)

Initial manually-installed APK run reported all ten cases `NOT_COMPLETED` and code `INSTRUMENTATION_INCOMPLETE_OR_FAILED`. Code review found the Python runner passed six-character IDs (`m23_01`) into a parser that requires the full Android method name (`m23_01MissingPrivatePathsAreNotDownloadApproval`). The report cannot establish whether device tests passed or failed.

The repair binds exactly ten full source-attested method names, accepts only a complete instrumentation success, converts the outcome back to stable case IDs, and persists only sanitized case statuses/final code, not raw device logs. Host regressions cover PASS, FAIL, missing cases, empty output, unexpected methods, and exit-code mismatch. No APK source changed; installed app and instrumentation APKs do not need replacement. Run the repaired script and inspect its result before any merge. Device provenance is still unverified without separate installed-APK digest checks.


## M23-CB: Primary Cinderbox app integration repair

The original `com.game.cinderbox` is the **primary game app**; Companion `com.sdvsync` manages its existing files. User-visible Android screenshots showed a structurally plausible imported game at `StardewValley/desktop/GameFiles`, a detected `smapi-internal`, and a missing independent `Download/StardewValley` path. Treat those as **distinct facts**. The original Cinderbox import is not a Steam manifest attestation, but it must not block an optional download into a *different empty folder*.

The Download tab now surfaces primary-game/SMAPI detection and opens Installation Health without Steam login, write probes, data moves or implicit repairs. Download eligibility is a separate `M23CinderboxFirstPolicy` path guard: refuse primary-root ancestors and descendants, symlinks, invalid paths, any existing/partial selected destination or missing access; allow *only an independent empty or absent target* to proceed to existing Steam, storage-capacity, explicit write preflight and owned-checkpoint validation. No discovery result itself authorizes downloading. `GameDownloadManager.startDownload` rechecks this gate rather than trusting UI state.

`copyToCinderbox` now refuses existing or partial main-game bytes and overlapping source/target paths before writing. No silent copy/replacement of game, saves, mods, or SMAPI. A future explicit review/backup transaction will be needed for game updates; the existing M10 selective verified repair remains independently gated.

The M23 original 10/10 synthetic Android outcomes remain historical on the earlier installed APK. This fix adds 3 independent synthetic Cinderbox-first Android methods, built into `com.sdvsync.test` by current CI. They must be run against the **new** matched APK after a successful build; running the old test APK cannot qualify these changes. The test runner preserves only sanitized case codes and never inspects actual game folders. A separate, consented read-only real-installation inventory, APK digest/signer provenance, access-provider permissions and authenticated integrity checks remain not qualified.

After applying this PR-scoped native Devtool overlay, run `./devtoolw m23-cinderbox-check`. After a new successful PR build, install both matching APK artifacts by explicit consent (same signer only), then run only the new lane:

```sh
python3 scripts/devtool/m23_cinderbox_first_device_run.py \
  --execute-synthetic-tests --serial emulator-5554 \
  --ci-run-id <NEW_RUN> --output "$HOME/cinderbox-m23-cinderbox-first.json"
```

Release and publication remain disabled. Do not rerun M14–M22 or the already-accepted ten synthetic M23 tests.
