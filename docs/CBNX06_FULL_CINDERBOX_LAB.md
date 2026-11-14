# CB-NX06 — Full Cinderbox side-by-side debug variant (LAB02A)

This build compiles the **real app module**, its Compose UI, Nexus queue, pairing bridge, journal and mod review logic. It is NOT the smaller standalone harness. The normal `:app:assembleDebug` and `:app:assembleRelease` build paths are unchanged. The extra hosted-only task is `:app:assembleCbnxLab`.

## Boundaries

- Lab package `com.sdvsync.cbnx06lab` is different from `com.sdvsync`. Lab app prefs, databases, files, cache, ModDownloadJournal and NexusPairingInbox are separate Android app-private data.
- Main Cinderbox game root points to `<lab app filesDir>/CBNX06_GAME_LAB`; `desktop/Mods`, `desktop/Saves`, `desktop/GameFiles` and `smapi-internal` are synthetic/private.
- Lab manifest excludes broad external storage permissions, release/package install, Shizuku and Steam/autosync/game download background services, widgets, FileProvider and **all NXM VIEW** handlers. Only launcher MAIN remains exported. Mod downloads still use the actual native code but their allowed root is app-private. App must not request root/Shizuku/SAF/all-files privileges.
- Local-only, opt-in pairing listens on **127.0.0.1:38472** in lab instead of production **127.0.0.1:38471**. Host check follows the selected port. The existing Firefox extension still uses the production port; **do not pair it to the lab** until a separately identity-isolated lab extension is built and physically verified.
- Steam sign-in/service and cloud-sync functions are NOT qualified in lab and must not be used. App's UI may contain screens not yet safe for active use. No live mod install, save sync, game install or rollback is authorized at this gate. No privileged permissions may be manually granted.
- This variant uses its own ordinary debug signing identity; it must be validated against its **own** hosted signer attestation and exact installed APK bytes before any physical qualification. It must not be compared against the production `com.sdvsync` signer.

## Acceptance levels

1. `LAB_SOURCE_GATES_PASS`: static deny rules and synthetic tests only; never evidence of Android install.
2. `LAB_HOSTED_APK_BUILT`: Gradle compiled, lab package and manifest checked, APK source/byte/signature provenance recorded by CI.
3. `LAB_PHYSICAL_READ_ONLY`: operator verifies both packages coexist, production app hash and production game folder unchanged; lab app package/APK hash equal hosted artifact; no privileged permissions or NXM interception. This is manual, not automatic.
4. `LAB_LIVE_PAIRING_AND_STAGING`, `LAB_INSTALL_ROLLBACK`, `RELEASE`: all pending and require separate evidence.

A source gate refuses unexpected hardcoded public-game paths, Kotlin compile-time usages that cannot be redirected, production intent interception, missing guards, and unsafe fallback patterns. **A source-gate refusal means DO NOT INSTALL**, not that the gate should be weakened. No production installation/uninstallation/data cleanup is performed by any script in this change.

## Termux instructions

```
python3 /storage/emulated/0/Download/CBNX06_FULL_CINDERBOX_LAB02A_CONSOLIDATED.overlay.zip --offline-test
python3 /storage/emulated/0/Download/CBNX06_FULL_CINDERBOX_LAB02A_CONSOLIDATED.overlay.zip
```

The launcher uses `$TMPDIR` for temporary staging, checks both PR pins, never force-pushes, makes one commit to the existing Android PR branch, verifies exact changed blobs and parent, and tracks CI. `--resume-only` checks a post-push state without making any changes.

**Do not run `adb install` yet**: the artifact must first pass hosted checks; independent device-side no-cross-talk and byte-identity evidence remains pending.
