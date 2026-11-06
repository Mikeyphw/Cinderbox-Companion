# M25-03 R2F — Shizuku diagnostic categories and bounded service connection

Base: merged `master` commit `69188fdbd000830c133069c186382e49e7df3f33` (PR #60).
New branch: `feature/m25-03-r2f-shizuku-diagnostics`.

## Why

On the verified API 36 physical device, root produced `R2E_GAME=NOT_OBSERVED`,
matching the stopped Stardew Valley process. Shizuku's instrumentation completed,
but its older nullable helper gave `UNKNOWN`, concealing whether Shizuku was denied,
its Binder wasn't ready, UserService couldn't connect, a remote call failed, or
the privileged `pidof`/`ps` inspection was inconclusive.

## Changes

- Keep the same no-input privileged AIDL method and UserService version 2.
- Shizuku returns a fixed enum: `RUNNING`, `NOT_OBSERVED`, `BINDER_NOT_READY`,
  `PERMISSION_DENIED`, `PERMISSION_CHECK_FAILED`, `SERVICE_BIND_FAILED`,
  `SERVICE_TIMEOUT`, `SERVICE_DISCONNECTED`, `REMOTE_CALL_FAILED`, `PROCESS_UNKNOWN`.
- Connection can be attempted twice only, with 2.5-second and 1.5-second waits
  and a brief 150-ms delay. No automatic permission prompt or destructive unbind.
  The privileged service already has a four-second internal process timeout.
- `queryGameStatus()` remains backward-compatible, returning an `Int?` for the
  original Shizuku-first/root-fallback flow. `queryGameStatusDiagnostic()` is
  opt-in and returns only a fixed reason. All unknown outcomes remain unknown.
- The existing read-only instrumentation test emits one additional fixed receipt
  `R2E_SHIZUKU_DIAGNOSTIC`, without raw logs, PIDs, paths, or credentials.
- Ten pure Kotlin tests cover status decoding and retry policy. Hosted CI compiles
  the Android app, AIDL and instrumentation, and runs the API36 policy emulator.
- This is NOT an installed physical-device qualification, live game-idle lock,
  release approval, or permission to write to real game Mods folders.

## How to qualify on the phone

After hosted CI passes, install the *matching* `R2F_SHIZUKU_APK_PAIR` artifact
using `adb install -r` (and `-t` for the test APK) with explicit consent, then run:

```sh
zsh scripts/devtool/m25_r2f_shizuku_device.zsh --serial localhost:5555 --ack-read-only
```

A result like `PERMISSION_DENIED`, `SERVICE_TIMEOUT`, or `PROCESS_UNKNOWN` identifies
which layer to address, without permitting any mod mutation.
