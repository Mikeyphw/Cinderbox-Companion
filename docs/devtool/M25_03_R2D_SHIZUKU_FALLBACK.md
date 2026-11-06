# M25-03 R2D-S1 — Shizuku-first game-process status

Pinned parent: `d460210c7355b23cba221108e48c04e71ec4c8ff`. Branch: `feature/m25-03-r2-journaled-bulk` (PR #60). No release or live Mods write enabled.

## Behavior

The explicit **Check game status** action will first use Cinderbox's existing Shizuku `FileService` user-service when the Shizuku binder is running and permission is granted. The service UserService version is raised from 1 to 2 to avoid reuse of a stale Binder interface. It adds a **fixed-target, no-argument, read-only** AIDL method (transaction code 9) that runs `pidof` and `ps`, checking that it has root UID 0 or adb-shell UID 2000. It never accepts executable strings, paths or mod IDs from callers, and only returns `40` (running), `41` (not observed), or `0` (unknown).

If Shizuku is absent, ungranted, unavailable, timed out, or returns unknown, the existing bounded root probe is the fallback. A Shizuku 40 or 41 result skips the root prompt. No results are cached or logged as private process inventory. Errors are `UNKNOWN`, not `NOT_OBSERVED`.

**Crucial:** `NOT_OBSERVED` is still only a point-in-time observation. `GameSessionSafety.permitsLiveBulkWrite` is **always false**. The current Mod Manager bulk preview stays read-only, while existing isolated R2C transaction fixtures remain available for tests only. No arbitrary root/Shizuku shell APIs or new filesystem-write methods are exposed through this change.

## Required acceptance

- Source safety and prior R2A/B/C/D gates remain green.
- New five-case provider fallback JVM test and original eight-case game-status suite run on GitHub Actions.
- New AIDL/Android code compiles via GitHub Actions only; R47/R48A unchanged.
- **Physical Shizuku permission/service and actual game-running behavior require separate opt-in device qualification**; hosted success does not prove either.
- Root process identity is not an authoritative game-idle lock. A future live-write gate must also prevent game relaunch during the entire transaction and prove storage/recovery durability.
