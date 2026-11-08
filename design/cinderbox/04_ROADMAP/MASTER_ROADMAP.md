# Cinderbox Companion — Approved Dark Portrait UX: Complete Implementation Roadmap

**Decision (Nov 6, 2026):** User approved the **fixed full-app portrait mockup exactly as laid out**, but wants it **dark by default**. This approval supersedes alternative layouts and earlier brainstorming. Implement this design for the WHOLE app, not merely Mods. Prior Shizuku/root (R2F) qualification is deliberately **deferred until AFTER the new UX is implemented**; keep existing safety checks passing throughout. The reference is not an Android app; the native implementation must reproduce the visible hierarchy and behavior using Compose and Android platform conventions.

## 0. Strict reference/fidelity rules

1. **Canonical appearance:** `01_REFERENCE/cinderbox-portrait-DARK.html`; canonical machine contract: `02_CONTRACT/ux-contract.json`; 24 portrait PNG goldens: `01_REFERENCE/screenshots/` and `02_CONTRACT/browser-layout-golden.json`.
2. Do not redesign, rearrange, replace icons, or eliminate any approved sections. No new default tabs, no debug-like visual language, no marketing redesign that changes the approved home hero, card order, segmented controls, borders, spacing, or bottom navigation.
3. Dark must be startup default: backgrounds #101915, elevated surfaces #1b2922/#22362b, text #ecf5e9, green #8cd9a8, amber #eebc78. Derive the rest exactly from the JSON and CSS. Preserve the approved landscape/farm hero artwork, its geometry, and accents. Dark is the ONLY supported theme; no light, normal, classic, earthy or system modes or switches.
4. Preserve Home / Game / Saves / Mods / More with that order; Mods has Discover / Installed / Updates / Profiles; Saves has Local / Cloud. All the 15 secondary screens and their triggers must map to real Compose routes. Translate data to live models without inventing a different screen structure.
5. Steam is **optional**, no login at startup, no forced login navigation. Unauthenticated **Steam game downloads, Steam Cloud saves and Cloud sync are disabled**, while local saves, backups, mod management/discovery, profiles, Game health, More work. Nexus is independent. Actual privileges and entitlement are stricter than demo state.
6. The mockup contains **illustrative data**; live Android must not present it as real results. Explicit loading/empty/denied/offline/inconclusive states reuse the same visual style. Do not show fake installs, real-game write approval, fake compatibility status, fake percentages or fake Steam cloud connection.
7. Android-specific accommodations permitted only for system bars/insets, accessibility fonts, back gesture, density, and safe areas. Deviations require explicit documented evidence; no broad aesthetic discretion.
8. Enforce using the source-pinned HTML tests **and native semantics/screenshots**, not only hand-inspection. See `02_CONTRACT/ANDROID_PARITY_SPEC.md`.

## 1. Core architecture & baselines

- Use existing `~/Code/Cinderbox-Companion`, **no additional checkout**. `master` after R2E merge: `69188fdbd000830c133069c186382e49e7df3f33` when this handoff was generated. PR #61 R2F is open (head `cfbe9693473a32b9a80d225b1215b25b720cdfb6`, 7/7 CI passed at snapshot); verify latest GitHub before creating or applying overlays. Never blindly reuse that old base.
- Keep known pre-existing routes / deep links stable where possible (`home`, `game_download`, `saves`, `mods`, `settings`, existing mod/save detail paths) and redirect gently rather than breaking bookmarks.
- Kotlin + Material3 Compose; StateFlow ViewModels, stable state + one-shot effects, previews with deterministic fixture provider. Shared tokens in one `CinderboxDarkTokens` source. Compose `testTag`s from contract on every significant view.
- Design a `SteamCapabilityGate` or equivalent: separate **authentication**, **entitlement**, **network**, **installed local game state**, **cloud availability**. UI alone must never unlock privileged downloads.
- Network/provider adapters behind capability interfaces; cached/partial data must declare provenance and freshness. Keep the Nexus-specific API-key and NXM behavior permitted by provider terms.
- State restore across process death, permission prompts and back navigation; no auto-install from browser or deep link.

## 2. Implementation workstreams (build the whole approved UI first)

| ID | Screens and work | Required completion evidence |
|---|---|---|
| **UX-00** | Steam-optional launch: remove startup login gate; initialize Home local; Steam connection via Home and More; explicit disconnected UI in Game and Saves; Nexus separate. | Hosted tests prove local onboarding Home, no login activity redirect, local files + Mods available, Steam download/cloud blocked before verified auth. |
| **UX-01** | Shared dark design: exact tokens, typography scale, icons, 5-tab shell, status/insets, hero, cards, buttons, navigation, transient sheets, toast, bottom bar, Android back, single dark only. | 393×852 and 360×800 reference screenshots and pixel+geometry checks; Compose semantics tags; dark tokens; TalkBack labels; no horizontal overflow. |
| **UX-02** | Home (hero, optional Steam connection card, at-a-glance, quick actions, recent activity, notification and transfer controls) + Activity/Operation center. | Exact approved arrangement, screenshot states local/connected/empty/loading/error, activity rows from source. |
| **UX-03** | Game: installed status cover, version/SMAPI summary, optional Steam download, protected destination, branch/files/SMAPI/health/recovery, download progress. | Source-scoped permission checks, existing M3 no-write gates, partial/interrupted download coverage, screenshot parity. |
| **UX-04** | Saves: local farms, two-pane Local/Cloud, farm viewer tabs (farmer, relationships, animals, bundles, museum, recipes), backups, sync history, conflict preview and cloud locked state. | Local path works offline; Cloud locked before Steam; explicit conflict resolution and restore preview tests. |
| **UX-05** | Mods/Discover: approved search hero, category chips, filter sheet, sort, grid/list, mod thumbnails, bookmarks, pagination, provider errors, mod detail gallery/files/requirements/version/compatibility. | Source API contract, search/debounce, pagination dedup, filters and bookmarks, fake-compatibility prohibition, screenshot parity. |
| **UX-06** | Mods/Installed, Updates, Profiles: approved segmented header, installed list, metadata, update previews, profile create/import/export/note, mod health, staged bulk review and snapshots. | Local inventory + version provenance; metadata import does not write Mods; existing R2 journal/source gates retained. |
| **UX-07** | More: account card, independent Nexus permission, Shizuku+root opt-in, storage SAF, notifications, appearance, auto-sync settings, advanced health/diagnostics, About/Help. | Provider-specific error states (R2F), permission request only on intent, Steam disconnected switches, no privileged access during browse. |
| **UX-08** | All 15 deep screens, cross-screen actions and shared download queue; align full navigation, modal and sheet interactions, sample-to-live state adapters, multiple display sizes. | Every reference state mapped to deterministic Compose fixture; no dead buttons; no broken back stack. |
| **UX-09** | Consolidated new UX finish: captions/text contrasts, keyboard/IME, screen reader, 200% font, dynamic type, offline retry, performance, functional device-ready APK. | Full-native CI parity source/semantics, screenshot goldens in two Android sizes, accessibility and failure-state suites. |

**Preferred execution:** cohesive source-pinned Devtool overlays with auto-commit and push; GitHub Actions provides Gradle, Java and Android emulator. User dislikes review-first gating—implement the planned phases and run available tests rather than asking for approval between trivial tasks. Use new feature branch(es) based on the current `master`, no force push/rebase/reset/no remote checkout. Avoid zsh special `path` variable. If R2F PR #61 is still open, account for it safely; don't overwrite its changes or merge it implicitly.

## 3. Qualification AFTER implementation — priority explicitly requested

User explicitly wants **work on the new full-app UI first**, then **qualify EVERYTHING afterward**. This means no detour into R2F device tests before UX-00..UX-09 implementation, but NEVER remove existing source safety gates during implementation. Qualify in the following sequence:

1. **QUAL-00 Reference fidelity:** Commit immutable HTML, dark token JSON, 24 screenshots and browser layout metrics under `design/cinderbox`; run GitHub workflow `cinderbox-ux-approved-reference.yml` on PR/push. This tests the *reference*, not native.
2. **QUAL-01 Compose fidelity:** Implement named `testTag`s and `UxReferenceParityTest`. Activate `cinderbox-ux-native-parity.TEMPLATE.yml` only when tests exist, and make it a required check for UI completion. Assert screen order, hierarchy, bottom bar bounds, palette, baseline insets, accessibility, state navigation, and no login redirect.
3. **QUAL-02 Screenshots:** Capture native API36 Android screenshots of the same reference screens with a fixture backend and constant clock; record Compose goldens and reject visible layout drift. A browser golden is NOT proof the Android layout matches. Use relative anchor geometry from browser; allow documented platform inset/font adaptations only.
4. **QUAL-03 Existing M25 & R2F:** Confirm R2A–R2E GitHub CI on merged master; finish PR #61 Shizuku diagnostics without hidden stale APK; test signed, SHA-verified app/test APKs on physical `localhost:5555`. Historic root `NOT_OBSERVED`, Shizuku `UNKNOWN` at R2E are **not** final R2F acceptance.
5. **QUAL-04 Device + operations:** Android 16 / API36 device, root KernelSU and optional Shizuku as explicit grants; Steam disconnected & connected flows (without exposing credentials), local save views, backups, cloud conflict guard, game entitlement, Mods browse/download staged install, recovery after process death, files permissions, background/foreground behavior.
6. **QUAL-05 Release/safety decision:** R2 production bulk modifications must remain disabled until a real reliable game-idle exclusion mechanism, power-loss transaction durability, rollback and independent evidence are qualified. Release/publish/device-install flags should remain false until actually justified. Summarize remaining gaps and release blockers clearly.

## 4. Interaction/visual parity checklist for every screen

- [ ] Same top bar title/eyebrow, action icons, section order and typography classes as reference; no obsolete technical boxes.
- [ ] Same dark background/card/line/chip/button colors; selected navigation tint; warm hero remains.
- [ ] Same scrolling behavior and sticky bottom nav; no loss of back navigation.
- [ ] UI includes disabled, empty, offline, loading and errors with proper actions; no crashes.
- [ ] Semantic labels/testTags assigned per contract; nav and panels retain names/order.
- [ ] Mock demo behavior mapped to secure real behavior (e.g. Steam auth, installed mod reads) but NEVER simulate successful file changes.
- [ ] Complete specific tests and evidence artifacts attached to GitHub Actions; no "source passed" used to imply device passed.

## 5. Not in scope unless separately requested

No redesign of approved layout, no new mandatory onboarding, no forced Steam, no Nexus Collections, no new global tabs, no modifying real Mods folders without independent qualification, no releasing or publishing a debug build automatically, no hidden tracking. Browser UI shell should not be shipped as a WebView replacement unless the user explicitly opts for that architecture—the app should remain native Compose with visual parity.

## CB-NX01 — First next deliverable (November 8, 2026)

The first new feature delivery after merged NEX-R5 is the **exact-file Firefox/NXM/Cinderbox
browser-assisted handoff**. Preserve the mod ID and the exact selected file ID from the
approved native mod details, through a signed-in Nexus browser session and the Stardew
Nexus Download Queue extension, to Cinderbox's guarded `nxm://` receiver. An archive
must still be staged for **mandatory user review**; navigating or opening an NXM link
is not evidence of download or installation. Source documentation:
`docs/devtool/CB_NX_FIREFOX_INTEGRATION_ROADMAP.md`.

CB-NX02 native persistent queue; CB-NX03 optional bidirectional pairing; CB-NX04
mod status reconciliation; CB-NX05 full extension UX; CB-NX06 release qualification.
These follow CB-NX01 rather than replacing its acceptance tests. The approved dark
five-tab layout and NEX-R5 community fallbacks remain unchanged.
