# M25-03 R2A — Journaled bulk transaction core (fixture only)

## Scope and security qualification

One rollback-only journal for 1–512 SMAPI dot-folder toggles. This is a new **internal** transaction engine and independent JVM/host fixtures. There is **no production/UI caller** of `ModBulkTransaction.apply()` in R2A. The existing R1 group/selection/review remains read-only. It cannot change user mods through this new code. This deliberately preserves the no-live-writes gate until R2B qualification.

### Preconditions

- Exact source-bound `master` from PR #59 and new feature branch.
- Root must be an available, writable canonical directory with safe platform aliases, not a symlink; direct-child names, all sources, all targets and case-fold uniqueness are checked.
- Only `foo ↔ .foo` names are accepted, not arbitrary renames; 1..512 bounded moves, unique source and target paths, no intersecting rename graph.
- Each selected source is recursively byte-hashed with no symlink traversal, non-regular entries, shared file hard links (when identifiable), or unbounded individual folder size/depth/count. Direct-child inventory/root identity is separately hashed.
- The preview ID, inventory fingerprint, root witness, exact moves and source digests are immutable. Revalidation occurs before writing the app-private journal, and byte digests are checked again during the operation.
- Journal written and `fd.sync()` called before renaming first source. Completed operations remove the journal. Interrupted operations always attempt reverse order rollback; nothing is overwritten or deleted.
- Recovery pre-verifies the full journal and every currently present folder against recorded SHA-256 before performing a single rollback rename. On ambiguity, *retain the journal* and block progress for manual inspection.
- Explicit individual SDK/game-launch-state witness and Android device qualification are NOT implemented here. R2A cannot be used for real changes.

### Failures and deliberately remaining gates

- Host/JVM fixture suite: 11 unit tests covering byte parity, inventory and byte drift, zero/513 and collisions, 512 dry-run, journal-only/partial/full process-death recovery, ambiguous collision, tampered moved folder, nested/target symlinks, root symlink, hardlink, deleted file and double approval.
- All test roots use Java temp directories. No Termux `Mods/`, phone, game data, `su`, Steam, Nexus or release changes.
- `fsync` on the file-backed private journal is invoked; Android/shared-storage directory-entry durability and hostile concurrent root/mount swaps remain to be qualified. A process owning root could race path inspection; this engine is not a malicious-root sandbox.
- No live production integration in R2A, and no APK is marked release-ready. R47/R48A test rosters and M25 profile/update rosters remain untouched.

### R2B must finish before M25-03 R2 is considered complete

1. Add an independent manager-owned *read-only* filesystem review of the selected normalized unique IDs, `ModSelectionPolicy.preview` compatibility/metadata fingerprint, and the new `BulkFolderReview`; no inventory getter with legacy folder auto-renames during review.
2. Check cross-journals (`ModBatchTransaction`, `ModProfileTransaction`, `ModSafety`) and storage path ownership prior to review and commit, plus the authoritative game-not-running/device gate (do not treat `ps` as proof).
3. Add explicit UI confirmation for the exact immutable folder/byte witness and the intended action; differentiate `APPLIED`, `REFUSED`, `MANUAL_REVIEW_REQUIRED`; keep selection and preview cleared on any inventory change.
4. Add independent Android API36 emulator fixture and failure-state tests with a separate M25-03 receipt; preserve historical R47/R48A rosters without overwriting them.
5. Requalify on actual device separately before enabling real shared-storage mutation, with release/device policy switches still false.

No Nexus Collections, automatic update, boot repairs, real account operations, real device install, root, or release signing are added.
