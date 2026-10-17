# Earthy UI detour — Cinderbox Companion

## Authority and scope

This source branch is based on post-M21 master merge commit `930ab17067dc6f8ed078bdb31efdcbd9f56e2899`. It does **not** change, backdate or replace any M14–M21 receipt. M21 is 18/18 on its original source; M14–M20 have 74 earlier historical passes (92 observations total). These are **not** passing tests for this new UI code.

The original accepted M22–M29 product roadmap remains: M22 baseline/evidence, M23 real installation discovery, M24 authenticated download correctness, M25–M29 safety, Android release qualification and distribution. **UI-D01–UI-D03 are a temporary visual detour**, not replacements for milestones.

## D01 implemented in this patch (pending CI)

- Original Earthy daylight and nighttime Material 3 palettes; existing Classic palettes unchanged and initially selected.
- App-private `cinderbox_appearance` DataStore with `EARTHY`/`CLASSIC`, `SYSTEM`/`LIGHT`/`DARK`, corruption handling and unknown-value fallbacks. Preferences do not depend on Steam, root, permission dialogs or save paths.
- App-wide reactive theme selection in `MainActivity`; signed-out and authenticated Settings share the existing `SettingsScreen` and can choose visuals without privileged operations.
- Color-aware shared action/gold/danger buttons, pixel borders, progress bars and navigation backing. Only the selected Earthy mode adopts new colors.
- Synthetic Compose preview + three read-only Android instrumentation tests. Static host contrast checks for eight functional foreground/background pairings. Both host and Android compilation must run on **exact changed source**; this document does not claim CI/device tests ran.

## D02/D03 remaining

- Complete audit of hardcoded colors (icons, background indicators, Steam badges, dialogs, upload/download states, Cinderbox wizard), Android UI contrast on 320–360dp screens and font scaling; preserve accessibility and explicit status/error text.
- Screenshot reference comparisons and optional original seasonal accents (avoid importing or tracing mod sprites).
- Source-bound GitHub CI, opt-in device tests, screenshots and actual APK artifact/provenance receipts. Merge only after checks, keep publication policy disabled.

## Legal boundary

Visual tone draws broad inspiration from DaisyNiko's **Earthy Recolour** and **Earthy Interface**; all Kotlin colors, shapes and text are original. No third-party mod artwork is shipped, derived, embedded or redistributed. Consult the original authors before using copyrighted mod assets.

## Safety

`docs/security/M3_RELEASE_POLICY.json` remains unchanged: no release, device qualification or publication approval. This patch does not install APKs, alter Steam sessions, mutate game/saves/mods, request permissions or run authenticated network work. CI should compile Android apps through GitHub Actions; never build them in Termux or chroot.

## Native Devtool overlay and execution (UI-D01)

The replacement artifact is a schema-v2 Devtool overlay, **not** a custom Python installer. It uses inventory source SHA-256 preimages and payload checksums, requires a clean worktree, applies atomically, validates the host gate, and commits only on success. Run `devtool --repo "$PWD" overlay check path/to/overlay.zip` before application, then `devtool --repo "$PWD" --yes apply-overlay path/to/overlay.zip --keep-artifact`. It expects a clean branch from the post-M21 base and rejects touching files with diverged contents. Historical M21 evidence is not regenerated.

`./devtoolw earthy-check` uses the dependency graph `security-contract -> earthy-source` with Devtool evidence history; `./devtoolw earthy-full` extends that graph through existing unit test, lint, debug APK and verifier jobs. GitHub Actions invoke **the identical** `ui_d01_gate.py` and upload its source-bound sanitized JSON as a CI artifact, in addition to the existing APK signature and provenance sequence. Android compilation and device qualification are not provided by the offline host gate.
