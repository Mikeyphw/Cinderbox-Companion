# CBNX06 LAB05 — Hosted API36 Android UI journeys (physical qualification deferred)

LAB05 adds a separate **real Android API36 emulator** Compose instrumentation lane to Cinderbox's isolated `com.sdvsync.cbnx06lab` build. It requires actual UI taps and a complete synthetic ModFileManager install/rollback in an app-private LAB Mods root. The four named cases are run independently with strict instrumentation event counts, a SHA-bound receipt and fixed, redacted failures. Gradle runs only in GitHub Actions.

1. Unpaired consent is visible but disabled even after starting a code window.
2. Cancelling an install leaves the Mods root and LAB04 transaction journal untouched.
3. Cancelling a synthetic exact-file request preserves the private inbox; no browser is launched.
4. User-confirmed synthetic installation invokes the real reviewed installer, then snapshot-backed rollback and verifies an empty isolated Mods root.

The runner validates `ro.kernel.qemu=1`, API36 and absence of production Cinderbox, installs only the isolated LAB APK and its instrumentation APK, and deletes raw logs even when a test fails. A bounded `STATUS.json` retains the four outcome codes and source, app and test-APK hashes; it does not contain user file IDs, paths, pairing secrets, browser tokens, or stack traces.

**Scope exclusions:** No Iceraven installation, live Firefox pairing, Nexus login, remote downloads, production Mods/Saves reads, physical-device assertions, game-byte immutability, release, publication or merge. LAB03B physical qualification is still deferred; this lane is not a substitute for LAB06 physical acceptance.
