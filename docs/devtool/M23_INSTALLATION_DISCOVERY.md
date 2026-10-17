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
