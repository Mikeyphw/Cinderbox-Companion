# R48B R1 — Real compact-screen header correction (not release/device)

## Provenance and scope

R48A `41907724611` succeeded with 4/4 Android instrumentation tests and 5/5
independently verified PNG captures from a zero-account hosted API36 emulator
(320dp wide, 160% text). The artifact `13362046220` was inspected visually.

Observed issues on the real app's first viewport:

- Game: the title `Download Game` is visibly ellipsized as `Downloa…` because
  the mandatory Steam badge occupies the same 64dp bar as the back button/title.
- Mods: the `Mods` title is completely crowded out by the Steam badge, Backups,
  and three top-bar actions. All these actions must remain available.
- Saves: the offline empty-state title says `No saves found on Steam Cloud`,
  although this fixture is explicitly offline. That is a *separate copy fix*;
  the current R48B R1 overlay intentionally does not change saved-file behavior
  or copy until a screenshot requalification of the compact header is complete.

## Implementation

The shared `StardewTopAppBar` now uses `BoxWithConstraints` to detect widths
under 420dp and keeps the actual title + back control in the Material 3 bar.
The existing Steam badge and screen-owned actions move to an adjacent, theme-
colored wrapping `FlowRow`. On wider panes, the existing one-row presentation
is retained. Both Classic and Earthy palettes remain enabled; the lower pixel
border now surrounds the combined header. No click handler, access permission,
authentication operation, retry, update or file-system behavior is changed.

## Acceptance

1. Source gate `.github/workflows/r48b-compact-header-source.yml` must pass.
2. Existing R48A real-activity workflow must run at **this PR head**, compiling
   app/test APKs, passing all four tests and independently verifying five PNGs.
3. Download and visually inspect the **new** Game, Mods and Saves PNGs; assert
   Game and Mods titles are readable and all controls are visible/wrapped.
4. Continue with R48B R2 offline empty-state wording and more detailed large
   font/landscape checks only after above acceptance. R48C physical-device
   accessibility/consent and M25–M29 remain separate work.

The current source-only fixture is **not evidence of visual acceptance**.
`R43BLiveUpdatePolicy` booleans and the `M3_RELEASE_POLICY.json` denial states
stay disabled. No real Steam account, mods, save files, GameFiles update, root,
APK release signing, device install, TalkBack qualification or publication.
