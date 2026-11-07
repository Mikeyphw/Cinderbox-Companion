# UX-09D01 audited replacement — default-size functional and visual consistency

Source-locked baseline: `b9e7883e04431d49f12dda9337d2922f59c0e475`, tree `bac40b93a828adff39e2efa76aa2129bd680d415`. This package REPLACES both earlier unapplied UX-09D01 kits. Apply only this audited replacement.

## Product changes

- Android edge-to-edge now explicitly requests **light foreground icons for the dark status bar** using `SystemBarStyle.dark(Color.TRANSPARENT)`; the safe-area inset remains unchanged.
- Mods, Saves, and More get a brand header consistent in dimensions/palette with Home/Game, and all three use exactly one **Activity** action routed to the existing read-only Operation Center. Do not reuse generic arrow or plant glyphs for unrelated operations.
- Mods calls its primary page `Mods` and puts `Manage local mods` immediately under the pane selector, using the existing `onOpenAdvancedMods` route. The old buried, duplicate advanced-manager card is removed. Nexus search/key gates, sorting, browse, downloaded queue and installed-mod review are unchanged.
- Saves continues to expose sync history in the Saves body; More retains Help, About and settings as labeled entries. No invented farm/game/mod records or Steam login state.
- Existing Steam Login redesign, Back action, and protected file/import workflows stay unchanged.

## Hosted qualification

- GitHub Ubuntu 24.04 + Android API36 emulator ONLY. Builds and hosted instrumentation via Gradle GitHub Actions, never local Termux.
- Two standard font viewports: `786×1704` and `720×1600`, 2× density, `font_scale=1.0` only.
- Six real offline MainActivity PNG + JSON cases (Mods, Saves, More × two viewports), requiring screen header top safe area and **status bar foreground light**, and correct dimensions.
- Functional instrumentation: Activity → **tagged** Operation Center → **tagged Back** → original tab on all three tabs; Mods → Advanced Mods → Back. Every navigation assertion has a bounded wait and named failure; no text-only route false positives. Failure blocks evidence qualification. No Steam authentication, mod writes, release/distribution or physical device acceptance.
- PNG CRC, IDAT decoding, actual pixel diversity, and matching image-content receipts are required before accepting screenshots. The sample gate rejects corrupt, flat, or falsified images; no Pillow install is needed.
- Source contracts also require CI triggers for `MainActivity.kt` and `OperationCenterScreen.kt` changes.
- Screen candidates are not pixel-parity approval or native golden approval. Browser reference and 24-case contract stay immutable.

## Safety and sourcing

Canonical Devtool ZIP adds nine files. Its validation runs source transforms in `--source-check` mode and hermetic tests. The outer installer checks Git exact source and blob preimages, then applies **five** existing source Kotlin changes (including two stable operation-center test identifiers). All existing Privileged operation, Shizuku/root, Steam and live update gates remain off. No source rewrite, force-push, local Gradle, or `git reset` is needed.

See `UX09D01_EVIDENCE.json` in the hosted artifact after the PR CI succeeds.
