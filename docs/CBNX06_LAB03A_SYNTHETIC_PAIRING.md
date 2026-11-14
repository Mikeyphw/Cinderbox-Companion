# CB-NX06 LAB03A — Synthetic archive review plus exact-file pairing emulator acceptance

Full Cinderbox lab package: `com.sdvsync.cbnx06lab`; existing production package `com.sdvsync` remains untouched. Builds on PR #89 commit `6999f8430357f78915c47efb7dcbfd02a93b69e6` and the separate Iceraven LAB02C source XPI in `Mikeyphw/scriptexts` PR #2 (`bcb7b15ff86cba5245441b2651ddd11d0aba349d`).

## What this phase does

- Keeps the existing native pairing flow: locally displayed 9-digit pairing code, 38472 loopback, explicit inbox handoff switch, exact `mod_id`/`file_id` and request ID, no automatic network/download/install from browser. Native inbox UI shows each request for local user choice. Production 38471 stays independent.
- Adds **LAB03A synthetic only** UI button, strictly for the full lab build. It generates a tiny deterministic ZIP containing a synthetic SMAPI manifest under `<lab filesDir>/cbnx06-lab03-synthetic`, verifies its SHA-256, passes the real `ModFileManager.previewFromZip` engine, refuses changed archives/receipts and checks lab Mods top-level metadata is unchanged. It never installs or represents a Nexus file.
- Adds a separate API36 **emulator-only** class of exactly two tests, one for private archive review, one for loopback consent, identity, repeated request and revoke. The test app cannot use the real Cinderbox game root, and the runner refuses an emulator with production `com.sdvsync` installed. Raw logs are deleted; the uploaded summary contains no tokens/codes/paths.
- Uses a build-property-gated `android.testBuildType=cbnxLab` only for the dedicated lab AndroidTest command. All default debug/release tests retain `debug` as the test build type.

## Qualified versus pending

Passing source gates or an API36 emulator run does **not** mean a real Nexus download occurred; there is no real downloaded archive, provider-backed file receipt or installed mod. It also does **not** qualify installed APK byte identity on the user's device or immutability of real Stardew data. These remain LAB03B/LAB04/LAB05 physical acceptance, followed by CB-NX07 release review.

**Do not grant privileged permissions or use live game save sync, installs or rollback in this lab phase.** Do not install/uninstall production Cinderbox, merge PRs, release-sign, auto-authorize downloads or expose tokens. In browser, keep NXM interception disabled in LAB02C and pair manually to `127.0.0.1:38472` only.
