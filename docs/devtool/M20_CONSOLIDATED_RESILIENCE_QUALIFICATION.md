# M20 — Consolidated Android Resilience & Recovery Qualification

## Source and qualification scope

One feature branch `feature/m20-consolidated-resilience`, one PR, one normal Debug APK CI build plus **one** Android instrumentation APK. Baseline: merged M19 `ae2ba76bbcdc2f99bd4e19545afe6ebe26fed8d3`. No added standalone CI workflow or duplicated APK builds.

Eight explicitly named lanes contain **52 exact instrumentation test cases**, declared in `scripts/devtool/m20_scenarios.json`. Source-host regression tests verify exact identity and number against `M20ConsolidatedDeviceTest.kt`, and the runner requires a full per-case PASS plus `INSTRUMENTATION_CODE: -1`. Absent/skipped/failed tests cannot qualify a lane. One all-lanes invocation produces `cinderbox-m20-consolidated-device` report, and separately run lane reports can be merged only if CI/source/APK/device identities and 52-case matrix agree with no duplicate lanes.

| Lane | Tests | Actual tested boundary | Limits |
|---|---:|---|---|
| A | 8 | Real Android service manifest/exported status; test-only, debug-variant foreground worker and production `GameDownloadRecovery` duplication guards | Not an authenticated Steam depot or live `GameDownloadService` transfer |
| B | 7 | Deterministic synthetic transfer chunks, disconnect, explicit resume and SHA verification | No real HTTP, TLS, latency, backpressure, or Steam backend |
| C | 8 | Production checkpoint negative paths; debug foreground worker; **real** `am force-stop` between c07/c08, PID disappearance and cold relaunch | Synthetic partial bytes; not an actual download transaction |
| D | 7 | Production ModProfileTransaction, ModBatchTransaction, SMAPI recovery, and review-policy fixtures | No actual installed mods changed |
| E | 6 | Production SaveRestoreTransaction, conflict/stale Steam Cloud presentation | No actual Steam Cloud account/saves accessed |
| F | 6 | Production StoragePlanner, InstallationScanner, safeDestination symlink/partial data policy | No destructive low-storage filling or permission revocation |
| G | 5 | Real signed-out Compose MainActivity Settings, Operation Center, Activity recreation and Refresh | No authenticated pathways |
| H | 5 | Synchronized checkpoint starts, simultaneous guidance, evidence privacy, owned-fixture inventory | Not a multi-process stress benchmark |

### Command line

```sh
# Host-only; no Android or installation effects
python3 scripts/devtool/m20_qualification.py --list-lanes
python3 -m unittest discover -s scripts/devtool -p 'test_m20_*.py' -v

# All eight lanes including real force-stop, on signed-out test installation with zero active jobs
python3 scripts/devtool/m20_qualification.py \
  --run-id <SUCCESSFUL_PR_CI_RUN> --transport termux-root \
  --all --ui-opt-in --test-profile-opt-in \
  --force-stop-opt-in --install --allow-replace \
  --output "$HOME/cinderbox-m20.json"

# A safe subset without force-stop; still installs CI debug APKs and exercises signed-out UI
python3 scripts/devtool/m20_qualification.py \
  --run-id <RUN> --transport termux-root \
  --all-safe-lanes --ui-opt-in --test-profile-opt-in \
  --install --allow-replace --output "$HOME/cinderbox-m20-safe.json"

# Individual lane (C also needs --force-stop-opt-in)
python3 scripts/devtool/m20_qualification.py \
  --run-id <RUN> --transport termux-root \
  --lane B --ui-opt-in --test-profile-opt-in \
  --install --allow-replace --output "$HOME/m20-B.json"

# Merge independently completed lane reports; checks identities and rejects overlap
python3 scripts/devtool/m20_qualification.py \
  --merge-reports "$HOME/m20-A.json" "$HOME/m20-B.json" ... \
  --output "$HOME/cinderbox-m20-consolidated.json"
```

### Fixture manager and inspection

Test-only `M20OwnedFixtures` canonicalizes Android's system-managed private `filesDir` alias *before* strict no-symlink checks; it never weakens the production `GameDownloadRecovery` symlink guard. Each test creates a random-nonce/hash `m20-owned-<24hex>` subdirectory with a verified ownership marker. A JUnit watcher only removes success fixtures; test failures persist for diagnosis. The debug-variant synthetic worker can write only within a validated owned fixture. No activity is driven by a production Steam login. Old M19 fixtures are inventoried as unverified; cleanup is refused unless journal, ownership marker, fixed bytes, and exact allowlisted directory shape match.

```sh
# Read-only; does not install or clear anything. IDs only, no raw paths.
python3 scripts/devtool/m20_qualification.py --inventory --transport termux-root

# Explicit, one-at-a-time removal of cryptographically bound owned test fixture ID
python3 scripts/devtool/m20_qualification.py --cleanup-fixture m20:<24HEX> \
  --maintenance-opt-in --transport termux-root

# Historic failed M19 fixture: cleanup only when strict M19 fixture checks pass.
python3 scripts/devtool/m20_qualification.py --cleanup-fixture m19:<24HEX> \
  --maintenance-opt-in --transport termux-root
```

M20 fixture cleanup refuses an unowned directory, symlink, unexpected top-level item, a too-large file, invalid nonce/ownership record, or a damaged legacy M19 checkpoint. There is **no bulk cleanup command**. Never `pm clear` or `rm -rf` to make a test pass. The read-only inventory itself must not create a registry folder. On-device maintenance requires installed M20 test APK and selected transport.

### Source provenance and safety

The runner checks local tracked source, PR-linked GitHub CI, M14-required host/build steps, M16 pinned signing, M3/M13 source hashes and both APK digests before any matching-signature install. It executes **only M20** instrumentation classes, never repeats M14/M15/M17/M18/M19 device workloads. All status reports remain `device_qualified=false`, `release_qualified=false`, `publication_allowed=false`. They do not authorize publication. The diagnostic classifier emits only stable categories and optional `M20ConsolidatedDeviceTest.kt` line numbers, never raw exceptions, logs, filesystem paths, nonces, secrets, account IDs or user files.

Real `am force-stop` kills the target process and can interrupt services. It requires independent `--force-stop-opt-in` **plus** signed-out test-profile confirmation, `--ui-opt-in`, and explicit APK replacement flags. Do not run on an active user's Cinderbox installation. One cold relaunch and test completion does not prove power-loss or network behavior beyond the explicit synthetic test fixtures.

### Acceptance and post-CI steps

Successful CI must include M20 host regressions, complete unit/lint/build, one isolated androidTest APK compilation and two M16 signer gates. Device evidence must contain 52 distinct PASS cases across eight lanes, `force_stop=PASS`, `process_gone=PASS`, `cold_relaunch=PASS`, and all provenance hashes source-bound to the same successful PR run. If Kotlin compilation or Android restrictions cause a failure, do not merge or interpret the source-only host tests as device qualification. Preserve the original evidence and use a source-pinned Devtool hotfix; rerun only incomplete M20 work.

## M20-C device lifecycle correction (post-first-device-run)

The initial device run for PR #25, source `db985f5b0e19011a53b8911a3376c22ec53c53ec`,
passed A (8), B (7), and C01–C07 (7). Before the planned force-stop,
`pidof com.sdvsync` returned empty. No stop was attempted and C08/D–H were NOT_RUN.
This is instrumentation-session teardown: an instrumentation PASS does not attest
that a live foreground worker remains running after `am instrument -w` returns.

The host now explicitly cold/warm launches the signed-out app, re-arms the existing
non-exported debug-only synthetic foreground service using the explicitly selected
privileged transport, and verifies a live service record + stable app PID. If Android
rejects starting the private service, if the service is not running, or if the PID
changes, force-stop is blocked with a precise non-sensitive error code. This
rearms only the app-private owned c07 fixture; it does not start production jobs.
The original 22 M20 passing case results remain historical evidence but must not
be treated as a full, single-source 52/52 result. New CI source provenance is
required after this source change. Do not rerun the older M14–M19 device suites.

### Device finding: G03/G05 navigation failure, Oct 16, 2026

Android 16 CI source `326d1045262c4be5955e96e2c3fdd614fb00fb0c`, CI
`38923143537`: A=8/8, B=7/7, D=7/7, E=6/6, F=6/6, G=3/5,
H=NOT_RUN; separately run C=8/8. Two failing G assertions had clicked
`onNodeWithText("Operation center")`, a passive Settings section heading,
not the real navigation button. M17 already qualified clicking the button
`View downloads, mod reviews, sync outcomes and recovery guidance` after
`performScrollTo()`. M20 G uses the same real button and checks the target
screen is displayed before refresh. Production UI and real user files remain
untouched by this repair.

Host diagnostics must classify only the respective failed instrumentation
status event: the previous implementation searched the *whole* multi-case
output, incorrectly attributing line 364 to both G03 and G05. Privacy-safe
exception categories and line numbers remain allowlisted; no path, raw stack,
nonce, or account data is published.

Preserve the C and A/B/D/E/F device results as historical evidence. For a
final strict source-bound merged 52/52 report, newly produced lane reports must
all share the updated source/CI checkout and APK identities; do not merge
receipts from different commits. First retest G and H against the new CI,
then execute other lanes for a final consolidated receipt if those pass.
