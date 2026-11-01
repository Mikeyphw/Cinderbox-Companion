# Cinderbox Companion: superseded R3 (standalone; do not apply R1/R2 first)

This artifact is a reviewable proposal based on the original uploaded 2026-11-01
snapshot, Git HEAD `bb659235e4408795e4b3daae3192b3c8dc6195f3`.
The public `master` branch was observed at `6213f11643010fe560c54642374c6a65854cde6c`,
and **is not this source**. Every modified file is SHA-256 preimage-locked;
never use checksum bypass to force a different tree. The exact source checkout is
required for validation; no files were pushed or installed.

## Coverage and fixes

R2 behaviors included: shared platform-owned Android storage alias validator;
Steam checkpoint/repair/discovery/mod integration; Kotlin JVM + instrumentation
coverage; host-first six-node native Devtool DAG; typed explicit GitHub Actions
plan/run/watch/artifacts wrapper commands; pinned official Gradle 8.11.1
checksum; SHA-pinned Node24 source-only CI and A07 concurrency correction. The source-only CI runs the base security
contract, A05/A07/A10, M19, M24 and M3H regression suites.

R3 findings/fixes: diagnostic messages now identify the exact unsafe
symlink component without embedding raw line breaks; dangling platform aliases
and NUL-containing paths fail closed; A07 source-frozen Python security command
uses `PYTHONDONTWRITEBYTECODE=1` instead of changing its protected argv;
Devtool offline contract rejects regression to write-capable parallel host
jobs; the source CI paths cover the recovery/repair/downloader sources and
Android instrumentation test. New JVM and Python negative tests cover these.

## Trust and execution boundaries

No Gradle is executed by this overlay validator, and `./devtoolw` defaults
to a Python-only host-check. **The existing explicit local Gradle aliases are
NOT removed**, and direct Devtool/Gradle commands remain possible. This is
host-first, not absolute hosted-only enforcement. A07 signed debug workflow
and A10 byte-frozen build.yml are preserved unchanged. New source-only CI
uses Node24 actions; legacy A07/other workflows may still contain Node20
and require separately coordinated upgrades. The R39 native hosted DAG,
exact versioned APK output, artifact import/signing and real-device download
behavior are not qualified or claimed by this artifact. No fresh hosted run,
APK or instrumented Android test is claimed as PASS.

Android alias trust is restricted to enumerated *exact* OS-owned path components
(e.g. `/sdcard`, `/storage/emulated`, `/data/data`). It does not permit symlinks
inside a user-owned game/mod path. This is a conservative preflight, not a
sandbox against root/mount namespace attacks or TOCTOU. Real devices can use
different aliases. Inspect the path in the app's own mount namespace before
extending the allowlist; the optional Termux inspector runs under `su` and may
see a different mount namespace.

## Apply / inspect when ready

```zsh
cd "$HOME/Code/Cinderbox-Companion"
devtool apply-overlay "$HOME/storage/downloads/CINDERBOX_DEVTOOL_STORAGE_SUPERSEDED_R3.overlay.zip"
./devtoolw host-check
devtool wrapper seal
python3 -B scripts/devtool/cinderbox_devtool_audit.py --json
```

The embedded script runs offline Python-only source tests and aborts/rolls
back the Devtool transaction on failure. Kotlin/JVM test execution in actual
Android Gradle CI, device testing, and stable signer checks remain external
acceptance steps. Do not interpret a successful apply as a tested APK.
