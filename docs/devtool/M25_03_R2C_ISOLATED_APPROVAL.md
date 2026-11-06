# M25-03 R2C — Isolated approval/commit integration

**Base PR:** #60, post-R2B/HF01 commit `8c14e410782cfaa8f70e4e5a0a9ecd09e843a096`.

R2C exercises a *real* ModFileManager → ModBulkTransaction path, but allows writes **only inside a direct app-cache fixture directory**. No production Mods/ path or user-visible apply action is authorized. This is deliberate: `GameProcessMonitor` polls via `su pidof` and returns `false` on failures, so it cannot supply an authoritative game-idle witness. A successful emulator test does not authorize changing live game files.

## Admission protocol

- A `ModBulkPreview` is returned only after both `ModCompatibility.preview()` and the byte-backed `ModBulkTransaction.review()` succeed.
- The owning manager retains the exact in-memory preview object and corresponding independent `BulkFolderReview`. An equivalent `.copy()` is not approval; all requests consume the pending review, including failed attempts.
- The commit gate checks canonical containment inside the app cache, exact direct-child `Mods` fixture root, and `PlatformStoragePaths.inspect` including unsafe symlinks.
- It checks all outstanding transaction journals, re-reads the inventory without legacy migrations, recomputes blockers/steps/fingerprint, and relies on `ModBulkTransaction.apply()` to independently reverify root, destinations, file hashes and fsynced journal before renaming.
- Successful changes use one journaled transaction; stale, replayed, colliding, blocked or out-of-cache requests fail closed. No production entry point is called from UI or ViewModel.

## Qualification

Host source gate and existing R1/R2A/R2B guards, hosted JVM transaction tests, hosted Android APK compilation, and **eight** API36 emulator fixtures. Source and receipt bound to PR head; physical hardware, release signing, publication and live bulk writes remain forbidden.

**Future R2D prerequisite:** a secure, authoritative game-not-running/storage ownership gate with race semantics, plus device-specific restoration and UI acceptance. Do not bypass this gate based solely on a process poll or an error interpreted as idle.
