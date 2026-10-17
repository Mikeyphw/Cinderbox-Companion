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

## UI-D02 implemented (stacked on successful UI-D01 CI)

PR #29 head `156bd65201a239b81ea7cd6f5a52e1ff68de8362` passed GitHub Actions run `39004991945` (all 43 CI job steps, including pinned debug APK and instrumentation APK compilation). UI-D01 is **not** yet merged or device-qualified. UI-D02 remains a separate, source-bound patch intended for a clean stacked branch at that D01 commit.

- Earthy-specific parchment cards/dialogs, forest-toned top app bar, and protected Classic fallback.
- Status-differentiated and theme-appropriate Steam badge colors (the existing retry authentication behavior is unchanged).
- Earthy empty-state pixel chicken, spinner, passive particles and setup wizard accent; original art colors retained in Classic.
- Money highlights in Save Viewer use tertiary Clay/Copper for Earthy only.
- Three synthetic Android Compose checks (Earthy day card/night dialog and Classic card) compiled only by future GitHub Actions; no real-device or screenshot claims.
- Host evidence integrates with a **target-local native Devtool DAG** `earthy-d02-check` (security → D01 → D02) and `earthy-d02-full` (reuses unit, lint, APK and verify jobs) and both existing GitHub Actions workflows.
- No operations on Steam sessions, installs, saves, mods, releases, or historic qualification JSON. Next UI-D03 audits 320dp, font scaling, focus/semantics and screenshot parity on device.

## UI-D02 Devtool overlay rehearsal notes

The initial Devtool artifact preflight for clean UI-D01 source was `ready`, structural/source checks passed with zero conflicts. The transactional apply ran six of six stages with zero errors and committed the synthetic test checkout; `earthy-d02-check` completed all three existing/new jobs. The full Python host regression suite finished with **294 tests, 0 failures, 1 skip**. No Android build/device test was run for D02.

**Known Devtool bug:** Rechecking the already-applied artifact exposed `NameError: sha256_file` in `devtool/overlay/conflicts.py:38`, not a clean source-mismatch report. Source preflight against the intended untouched D01 worktree and the actual apply are unaffected. This is tracked as `DEV-OVERLAY-CONFLICT-UI-D02-04` in the Devtool improvements ledger; do not interpret the internal exception as evidence of a successful fail-closed conflict classification.

## UI-D03 — accessible navigation + synthetic screenshot qualification (pending new CI/device)

Source baseline: UI-D02 PR #30 head `9dd7b387b3cd5a2a4a47d63f69e3367f4bb4efa8`, GitHub Actions Devtool Android Build run `39006846654` **SUCCESS**. That success is for UI-D02 only. This UI-D03 patch is **not yet compiled/qualified on Android**.

- Bottom navigation now provides `Role.Tab`, selected state, selectable group, 56dp minimum height and default visible interaction feedback instead of silent clickable targets.
- Pixel progress exposes normalized progress semantics to accessibility services; loading spinner exposes a localized loading state. All variants inherit the same accessible behavior, while Classic styling/palette remains unchanged.
- Source-bound host gate derives 16 WCAG 4.5:1 functional contrast ratios from the **actual Kotlin** Earthy light and dark Material schemes, not a separate static palette table.
- Android synthetic instrumentation tests cover tab role/selected click, 65% progress information, light and dark 320dp + 160% font-scale preview screenshots. Synthetic fixtures never load real Steam credentials or files and do not modify game data.
- Explicit `scripts/devtool/ui_d03_device_capture.py --execute-synthetic-device-tests --output-dir ...` can run tests on an already-provisioned debug device and export exactly two test-owned private PNG files via `run-as`. It never installs, uninstalls, signs, reboots, modifies permissions or claims to have verified the installed APK's source identity. PNG screenshots are synthetic, **not actual app screens**, and receipt `release_qualified` remains false. This is visual baseline evidence, not an automated pixel diff to DaisyNiko's assets.
- Native Devtool DAGs `earthy-d03-check` and `earthy-d03-full` reuse existing D01, D02, security, unit, lint, debug APK and verifier jobs; both GitHub Actions flows upload the same host gate evidence JSON.
- A real-device run and visual review are still required; post-D03 resume the M22–M29 roadmap unchanged.
