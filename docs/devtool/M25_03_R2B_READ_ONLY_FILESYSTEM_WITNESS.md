# M25-03 R2B — Filesystem-witnessed bulk preview (read-only)

Prerequisite: R2A commit `d6c63ce4d37dcad6800df8fcda9d5f7bba1d5660`, tree `47fcd36d818722aa1e049f016baa06b402e8fdbf`; PR #60 stays open until all R2 acceptance is complete.

## What this patch adds

- `ModFileManager.previewBulkWithWitness()` gets the active mod inventory without invoking the legacy `.disabled` renaming scan, runs all pending transaction recovery checks, runs the existing dependency and conflict policy, and hashes real mod folder bytes using the R2A transaction preflight. There is **no** live bulk apply entrypoint.
- The UI preview now distinguishes an all-source-byte filesystem witness from the metadata-only inventory fingerprint. Selection remains visible-only; a preview is neither an authorization nor a durable approval token.
- The ViewModel performs disk hashing on `Dispatchers.IO`, refuses stale selection/inventory responses and resets the busy state on failure. UI never displays untrusted file paths in error toasts.
- Recovery of pending bulk journals blocks other `ModFileManager` operations and does not claim success if ambiguous.
- API36 test builds and four dedicated instrumented fixture tests read/write only disposable directories under app cache; they never access real game data or require root.

## Deliberate limitations

No actual bulk enable/disable is exposed in the app. Required game-not-running authority, storage/identity guarantees and independent crash/recovery acceptance for production mutations remain unresolved. **R2B is NOT release, physical-device or production bulk-apply qualification.** Do not merge PR #60 as complete R2 until these conditions have been reviewed, or retain the feature preview-only explicitly.

The pre-existing legacy `.disabled` rename in `listInstalledMods()` is not changed here, to preserve the current explicit Android regression expectation. The new physical preview uses a separate non-migrating scanner; future cleanup of the legacy migration must be coordinated with its tests.

## CI expectations

GitHub Actions (no local Gradle): existing R47/R48 source and UI jobs, R2A JVM crash fixtures, new R2B source gate, hosted `assembleDebugAndroidTest`, and emulator-targeted R2B four-test fixture. All tests operate on fixture paths and do not provide real-device evidence. No release signing, Collections, or publishing.
