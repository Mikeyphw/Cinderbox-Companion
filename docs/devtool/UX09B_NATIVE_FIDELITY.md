# UX-09B — Native screenshot candidate evidence, not visual acceptance

Source base: `a55190953f89c8f7488e9ebfb3eb2246addf64f3` (merged UX-09A).
Scope: add-only hosted API36 screenshot test + image comparisons + source gates.

## Evidence and limits

UX-09A captured five broad main screens, but its `mods` PNG was captured **after**
visiting Discover/Installed/Updates/Profiles, so it is the **Profiles** state.
UX-09B captures each Mods section separately. It also captures the offline saves
cloud-locked pane, producing **17 genuine Compose samples** matching cases in the
24-case approved HTML set, at 393x852 / 360x800 CSS pixels and density 2.0.

Screenshots are produced from the *actual local-first MainActivity* on a freshly
provisioned offline hosted API36 emulator. They do **not** include synthetic farms,
installed mods, Steam authenticated state or real Nexus results. The browser
reference includes sample farm/mod data, so comparisons WILL show content drift;
this is not an excuse to copy browser screenshots and label them native.

`UX09B_EVIDENCE.json` contains per-case hashes, sample dimensions, semantics
bounds, navigation offset, mean RGB delta and heatmap image name. The 17 native
samples, 17 reference side-by-side differences, review Markdown and JSON are
uploaded as a CI artifact even if subsequent stages fail. In particular, the
receipt hardcodes explicit `false` for full 24-case parity and native golden
approval. It is *never* allowed to set these true based on image averages.

## Remaining UX-09B before acceptance

- Inject strictly isolated deterministic app-state fixtures for mockup's
  sample farms, mod images and count variants; no production credentials or
  hidden filesystem changes.
- Add the seven remaining 393px cases: Steam-connected Game, Steam-connected
  Cloud Saves, mod detail, operation center, download queue, file access,
  installation health; only fake session entitlements in the test scope.
- Measure native semantic bounds against browser anchor rectangles while
  specifying Android system insets, text scaling and font metrics. Fix the
  concrete layout differences; don't modify approved HTML goldens.
- After independent screenshot review, commit **native-only** approved goldens
  with complete source provenance, then activate strict future change detection.
- UX-09C then covers accessibility, 200% font scale, IME and lifecycle recovery.

## Safety

No production Kotlin, login, write, release, root or Shizuku source is changed.
Root/Shizuku and physical acceptance are separate later phases. Existing
`GameSessionSafety.permitsLiveBulkWrite` stays disabled, as do release, automatic
installation and publication. Never interpret emulator screenshot capture as
filesystem, account-entitlement or physical-device qualification.
