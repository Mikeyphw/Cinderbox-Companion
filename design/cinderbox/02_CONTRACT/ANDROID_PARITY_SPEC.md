# Auditable UI parity — what GitHub Actions can and cannot prove

## Binding sources of truth

- **User-approved geometry/content:** `01_REFERENCE/APPROVED_LIGHT_ORIGINAL_READONLY.html` (light original).
- **Approved implementation target:** `01_REFERENCE/cinderbox-portrait-DARK.html`; this has the approved dark palette, the single-dark-only Appearance card amendment (no alternate theme switches), and a single vital browser JS identifier fix, `top` -> `renderTopBar` (without which Chromium raises `Identifier 'top' has already been declared` and interactive UI stays blank).
- **Machine-readable requirements:** `02_CONTRACT/ux-contract.json`.
- **Golden viewport positions and colors:** `02_CONTRACT/browser-layout-golden.json` (24 states).
- **Visual screenshots:** `01_REFERENCE/screenshots/*.png` (16 states at 393×852 and 8 at 360×800).

## Immediate runnable test: reference browser

`03_CI/scripts/verify_layout_fidelity.py` pins the original approved light reference, the original approved dark reference, and the subsequent user-requested single-dark amendment by SHA-256. The browser image/geometry suite independently detects layout drift. `03_CI/scripts/verify_reference.py --verify` **launches real Chromium**, tests a blank-free initial render, all five global tabs, the four Mods sections, 15 supported deep-screen routes (a representative subset is snapshotted), local Steam-locked states, connected/disconnected transitions, JS-disabled fallback, dark palette, viewport overflow, 24 screenshots, and 24 sets of shell geometry (strict 2px tolerance).

Run locally/CI with Python + Playwright/Pillow, Chromium installed. For custom system browser, `CINDERBOX_CHROMIUM=/usr/bin/chromium`. GitHub Actions workflow file is under `03_CI/.github/workflows/cinderbox-ux-approved-reference.yml` (copy to repository `.github/workflows/` when adding the design folder). **Never auto-regenerate golden images on routine CI.** `--update-goldens` is for an expressly approved new design ONLY.

Browser image checks intentionally tolerate slight browser font rasterization (mean channel delta 7/255); 2px structural shell checks and immutable source hash provide independent guarantees.

## Native Android: required separate evidence

**A green reference job only means the HTML remains unchanged—it does NOT prove that Compose matches it.**

- Native screen roots and navigation controls must expose the `testTag` names in `ux-contract.json`.
- Use `03_CI/scripts/check_native_parity.py` to enforce tag constants, test function presence, dark tokens and hard-disabled live writes in source. This gate must **fail** while native work is missing.
- Build a real `app/src/androidTest/java/com/sdvsync/ui/ux/UxReferenceParityTest.kt` for hosted API36 instrumentation with the following `@Test` function names: `darkDefaultHome`, `optionalSteamFirstLaunch`, `offlineLocalSavesRemainAvailable`, `steamDownloadsLockedWithoutAuthentication`, `steamCloudLockedWithoutAuthentication`, `modsDiscoverAndSections`, `allFiveBottomTabs`, `darkThemeTokenParity`, `backNavigationAndSheets`.
- Capture *native* screenshots for those states with deterministic injected providers (no real Steam/Nexus data), disabled animations, fixed device profile/density/fonts; persist approved Compose goldens to repository only after comparing them against HTML screenshot reference and documented Android inset differences. Test both 393dp and 360dp classes where supported. On subsequent changes compare against committed native PNGs and bounds; fail on drift rather than using source regex alone.
- Add actionable `Accessibility` checks (content descriptions, font scaling, actionable touch targets, focus order, contrast) and failure-state fixtures.
- `03_CI/.github/workflows/cinderbox-ux-native-parity.TEMPLATE.yml` is a **template**, intentionally not immediately active until those test methods exist. Installing it early must fail; do not mask failure by marking tests as optional or skip.
- For Android instrumentation screenshots, use `UiAutomation.takeScreenshot()`, compare with native goldens in Java/Kotlin or via a stable GitHub-hosted Python processing step. Report native screenshot artifacts even on failures.

## Optional Steam must be a real authorization boundary

`No login` -> `Home local` and `Steam feature disabled` are functional access rules; verify UI and service-layer guards. Simulated `state.steam=true` only documents desired UI state, **not** actual Steam authentication or entitlement. Don't rely on button visibility as security.

## Repo install path

Place `01_REFERENCE`, `02_CONTRACT` and `03_CI/scripts` under `design/cinderbox/` in `~/Code/Cinderbox-Companion`; move the `.yml` under `03_CI/.github/workflows/` to the repo's `.github/workflows/`. Reference checker path detection works from this target layout. Do NOT put prior historical ZIP handoffs in the Git repo. See `06_HANDOFF/REPO_INTEGRATION.md`.
