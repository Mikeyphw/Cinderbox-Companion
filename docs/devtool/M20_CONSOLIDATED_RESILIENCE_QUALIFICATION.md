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
