# M19 — Interrupted Operation Checkpoint & Recovery Qualification

## Scope

M19 qualifies a **real Android process force-stop and cold relaunch** between two AndroidJUnit4 instrumentation stages that exercise the actual production `GameDownloadRecovery` and `OperationCenterPolicy` implementations. The operation is a **disposable, simulated partial Steam download** — no Steam login, network request, game installation, or real job is started.

Source baseline: merged M18 `cbc1fe5d82a058030ae7463ea8aa7a617f47018c`.

### Stage A: disposable checkpoint

1. Display the actual signed-out Cinderbox `MainActivity` via Compose test rule.
2. Generate a 128-bit random nonce on the host, never include it in the report.
3. Resolve an app-private, `m19-test-only-*` nonce-hashed fixture under `filesDir`. Refuse an existing fixture or symlink; never use an external path.
4. Invoke the production `GameDownloadRecovery.beginNew()` on the disposable checkpoint directory.
5. Write fixed, synthetic 4096-byte partial content inside the private fixture and verify bytes and checkpoint matching.

The host then cold-launches Cinderbox to establish a live process, runs `am force-stop com.sdvsync`, proves `pidof com.sdvsync` returns no process, and explicitly launches the Activity again. This is actual force-stop/relaunch, not merely Activity recreation.

### Stage B: recovery and cleanup

1. Launch the same signed-out app in the new instrumentation session.
2. Read the production `GameDownloadRecovery.pending()` checkpoint from the disposable fixture and verify persisted ownership/session marker and unchanged synthetic content.
3. Confirm that a changed Steam branch fails `requireMatching` and that a duplicate `beginNew` is refused. Neither may alter partial bytes.
4. Confirm the production `OperationCenterPolicy.build()` returns `ACTION_REQUIRED` and manual review guidance for `journals=setOf("download")`.
5. Explicitly discard the disposable checkpoint. Confirm that discarding leaves synthetic partial bytes intact, then remove only the exact allowlisted, nonce-scoped fixture entries.

The test does **not** claim a live Steam download automatically resumes after a crash. It does **not** prove recovery of a real game, failed storage devices, save restoration, active background services, or arbitrary interrupted transactions. It demonstrates one production checkpoint's durable, fail-closed recovery semantics with synthetic bytes across actual force-stop.

## Safety preconditions

- Use a dedicated, intentionally signed-out Cinderbox test installation, not an active user's Steam session.
- No active Steam, game download, mod operation, backup, restoration, or sync job. `am force-stop` will stop services and can interrupt active work.
- The M19 runner requires explicit `--ui-opt-in`, `--force-stop-opt-in`, `--test-profile-opt-in`, `--install`, and `--allow-replace`. Merely validating or applying the Devtool ZIP does not run on Android.
- APKs must come from a successful, source-bound GitHub CI job and pass M3/M13 artifact checks and M16 pinned signing. Installation never uninstalls or clears app data automatically.
- If stage B fails, the private nonce-scoped fixture may remain in Cinderbox private storage. This is deliberately fail-closed: do not attempt recursive cleanup or delete user state to make the test green. Investigate before another run.

## Workflow

From the M19 feature branch, use `./devtoolw m19-check` for host regressions. CI compiles one Android instrumentation APK containing the M14–M19 classes; the **device runner selects only the two M19 methods**.

After a successful PR CI run (replace `<RUN_ID>`), run on an explicitly authorized Android 16 test device:

```shell
python3 scripts/devtool/m19_device_qualification.py \
  --run-id <RUN_ID> --transport termux-root \
  --ui-opt-in --force-stop-opt-in --test-profile-opt-in \
  --install --allow-replace \
  --output "$HOME/cinderbox-m19-device.json"
```

Successful output: `overall: PASS_INTERRUPTED_OPERATION_RECOVERY_AUTOMATION`, both M19 instrumentation methods PASS, process disappearance and cold relaunch PASS, `fixture_cleanup: PASS`. A successful M19 check **never** sets `device_qualified`, `release_qualified`, or `publication_allowed` true. M14/M15/M17/M18 suites must not be reexecuted to establish M19.

## Evidence and improvement ledger

- M18 proved only a private marker survived process death. M19 now uses a real production checkpoint and the production status presentation policy.
- Keep source, GitHub PR and CI checkout SHA, APK hashes, and sanitized per-stage JSON, not raw personal paths or credentials.
- Deferred: a separate milestone to simulate real DownloadManager/Service worker interruption under disposable file providers; another to qualify external real game/save operations with user-authored backups. Those cannot be inferred from M19's synthetic checkpoint.
- If a Kotlin AndroidTest dependency/API compile error appears, fix via a source-bound Devtool hotfix and rerun CI before device execution; never claim host Python regressions prove Kotlin compilation.

## M19 first device run / targeted remediation (2026-10-16)

- PR #24 source `3439f92690230957aad79f1e213c35c86f5b2548`, CI run `38874701776`: CI passed, both APKs installed, but `seedInterruptedDownloadCheckpoint` failed (0/1) before force-stop, and the recovery stage did not run. Previous M14–M18 device evidence remains valid.
- Plausible root cause: the synthetic test fixture was based on the raw Android `filesDir`; on Android a platform-owned `/data/user/0` path alias may be a symlink. `GameDownloadRecovery.safeDestination()` correctly rejects any symlink ancestor. The exact live stack was not captured in the original report, so treat this as a hypothesis until verified.
- Remediation: use `filesDir.canonicalFile` **only for the nonce-scoped, app-private M19 fixture**, preserving production symlink rejection. Add host regression contracts and allowlisted category/source-line diagnostics for both M19 stages. Never print/store raw stack traces, private paths, or the random nonce.
- Status: host validation pending at packaging time; Android compilation and real-device requalification must still pass. No automatic uninstall, data deletion, or force-stop on validation.
