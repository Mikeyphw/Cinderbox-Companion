# Cinderbox Companion x Stardew Nexus Download Queue — Active integration roadmap

**Priority established:** 2026-11-08. **Status:** CB-NX01 IMPLEMENTATION CANDIDATE; not qualified. **Repository baseline:** `Mikeyphw/Cinderbox-Companion`, `master` commit `d47de2de163362130cc14e0256b45265fec0f5d2` (NEX-R5 merged by PR #84). **Extension baseline:** `Mikeyphw/scriptexts`, `main` commit `3008b994462352ee6c7a7a07702c6144287d9bdf`, path `extensions/stardew-nexus-download-queue/`. Recheck both heads before implementation; these are audit provenance, not permanent targets.

## Decision: CB-NX01 is the FIRST NEXT deliverable

The **first deliverable** is an **exact-file, browser-assisted Nexus download handoff** from the approved *native* Cinderbox mod-detail Files & versions section through the Stardew Nexus Download Queue Firefox extension back to Cinderbox's existing `nxm://` receiver, ending with the existing **mandatory archive staging and installation review**. Do not start with a shared queue, paired browser bridge, UI redesign, or new global tab. Ship only after the CB-NX01 acceptance conditions pass. The later milestones below implement the extension's full feature set.

### Confirmed current source constraints

- **NEX-R5 native details** now uses `ApprovedModDetailScreen` on `mod_detail/{modId}/{source}` and binds the per-file `nex.r5.download-for-review` action to `ModDetailViewModel.installFile(fileId)`; the legacy `mod_detail_advanced` route is secondary. Do not regress this, description formatting, Posts/Media browser fallbacks, or accepted dark-layout hierarchy.
- `ModDetailViewModel.installFile` currently requests `NexusModSource.getDownloadUrl(modId, fileId)` directly. For a non-Premium/free-account restriction it offers a **generic** Nexus Files tab URL, losing the selected `fileId`; it does not yet issue a file-specific browser handoff.
- `MainActivity` advertises `ACTION_VIEW`/`BROWSABLE` for `nxm` and retrieves `key`/`expires` before invoking `NexusModSource.getDownloadUrl` and `ModDownloadManager.startDownload`. Its NXM parser currently needs explicit game-host, exact-path, positive-ID and expiry validation.
- `ModDownloadService` has a single current job and one shared `ModDownloadManager._progress`; the archive is enqueued into `ModReviewQueue` for **explicit review**, not silently installed. Do not describe this as a persistent multi-item queue.
- The extension already has Nexus page click interception, manual/manager URL resolution, `ENQUEUE_DOWNLOAD`, a browser queue, status chips and remote-update checks. Its `launchManagerUrl` currently treats successful tab creation as completed handoff, **not proof of Android delivery**. It has no trusted native-app bridge and is a **Firefox extension, not a userscript**.

## CB-NX01 — Exact file, Firefox -> NXM -> Cinderbox (FIRST; no queue redesign)

**Goal:** From a **specific mod-file row** on the native Cinderbox details screen, a user can select browser-assisted download. Firefox opens the exact Stardew Valley Nexus mod, the installed extension identifies the exact selected file, resolves its legitimate mod-manager `nxm://` link using the user's Nexus website session and normal site requirements, and the Android intent is handled by Cinderbox, which downloads the archive to staging **for mandatory review**.

**Functional contract**

1. Add a pure, tested per-file handoff URL builder near `NexusModPageLinks`, e.g. `https://www.nexusmods.com/stardewvalley/mods/{modId}?tab=files&cinderbox_file={fileId}&cinderbox_mode=nxm`. Both IDs are validated positive decimal strings. These query names are **our proposed bridge contract**, not Nexus-provided API parameters. Use only genuine HTTPS Nexus domains and valid Stardew mod routes. Keep other Nexus navigation links unchanged.
2. On each `nex.r5.download-for-review` row offer **Automatic (API then browser fallback)** and/or a discoverable **Browser + NXM** option; preserve the file ID end to end. A failed direct API request that permits browser fallback must expose the **file-specific** URL, not the generic `?tab=files` page. A permanently unavailable/deleted file must not be substituted or retried as another file. Clear error states and user intent control must survive configuration changes.
3. In `scriptexts/extensions/stardew-nexus-download-queue/src/content.js`, validate the canonical mod ID against the page and requested file ID against the actual available file row before invoking the existing site-authenticated URL resolver. Refuse missing, ambiguous, deleted, incompatible or changed file identities. Respect login, download timing and account restrictions: no fabricated CDN URLs, bypasses, cookie extraction or undisclosed requests.
4. In `background.js`, distinguish **NXM launch attempted**, **Android acknowledged** (only if a future, verifiable acknowledgement mechanism exists), **download in progress**, and **downloaded/installed**. For CB-NX01, a successful `browser.tabs.create({url: nxm})` is only *handoff attempted*. Never record it as downloaded/installed in extension badges.
5. In Cinderbox, extract a testable NXM URI validator. Require scheme `nxm`, host `stardewvalley`, exact `/mods/{positiveId}/files/{positiveId}` path with no extra segments, bounded `key`, numeric future `expires` within a defensible time window, and graceful errors. Never log full NXM URLs, keys or tokens. Keep actual Nexus API download request behavior and existing manual review interlock.
6. Android external-app invocation may be restricted without a fresh user gesture. Provide a visible **Open in Cinderbox** fallback and actionable messaging instead of claiming silent handoff succeeded. If Firefox or the extension is absent, the original Nexus site must remain usable; the app should say how to proceed without guessing that the extension is installed.
7. Keep the approved five-tab dark app layout unchanged; use existing Mods detail/file UI, not a WebView or new top-level Queue tab. No live browser automation without explicit download intent.

**CB-NX01 completion criteria (all required):**

- [ ] Exactly the tapped `fileId` reaches the browser and the resulting `nxm://` request; `modId`, game domain and route must match at each hop.
- [ ] Free/non-Premium flow works with an authorized, logged-in Nexus browser session in a real Firefox for Android test; mandatory Nexus wait/confirmation and browser external-app prompts are handled. CI fixture success alone is insufficient.
- [ ] Valid NXM starts **one** guarded archive download; invalid/expired/mismatched NXM does not enqueue anything; duplicates and quick double taps do not create repeated downloads.
- [ ] The existing `ModReviewQueue` receives a real archive on authorized success, and the Mods folder is unchanged until user explicitly reviews/approves it.
- [ ] Extension missing, no browser, offline, login required, file removed, rate limit, permission denial and external-app prompt blocked all have testable, truthful fallbacks.
- [ ] Existing NEX-R1..R5 source gates, JVM tests, Android 36 emulator instrumentation, Firefox extension JS/DOM fixture tests, and a physical Firefox-to-Cinderbox handoff receipt are independently recorded. No fake device pass, fake download success, release claim, or signing claim.
- [ ] Source changes stay isolated on feature branches in **both repos**, use source-pinned consolidated Devtool overlays, GitHub Actions for Gradle/Android device tests, and commit/push/PR records. Never overwrite unrelated work, force push, or merge without CI evidence.

**Recommended implementation split:** Cinderbox: pure link builder, settings/fallback UI, NXM validator/unit tests, instrumentation. Scriptexts: strict `cinderbox_file` bridge handler, manager-link result state, extension fixture tests. Integration: Nexus free-account and Android OS external-handler acceptance on a real paired device.

## CB-NX02 — Native queue and download lifecycle

Implement a persistent native multi-item queue with exact file IDs; pause/resume/cancel/retry/reorder, dedupe, concurrency limits, crash/process-death restoration, file integrity and provenance, and reliable status notifications. Distinguish queued, resolving, handoff attempted, transferring, staged for review, installed, failed, and cancelled. Migrate from the current single-job service without weakening `ModReviewQueue`; do not treat the Firefox queue as native persistence. Prove restart, cancellation and rollback behavior with hosted and device tests.

## CB-NX03 — Optional authenticated bidirectional Firefox bridge

Add user-initiated pairing/capability detection and a locally scoped, authenticated, versioned protocol that can exchange queue state/status without exporting Nexus API keys or browser cookies. Prefer a documented secure mechanism that Android Firefox actually supports; do not claim that Android deep links alone provide a live two-way channel. Require consent, replay protection, bounded requests, disconnection/revocation, and tests for unpaired/expired peers. Fall back to CB-NX01 handoff if unavailable.

## CB-NX04 — Mod status and update reconciliation

Preserve the extension's downloaded-status chips, cached Nexus metadata, update glow and force refresh, but base **Installed** on verified local manifests and **Downloaded** on actual completed transfers, not on a browser tab launch. Match mod and file/version provenance before declaring updates. Surface uncertainty, stale data and unknown compatibility explicitly; sync status into existing Mods / Installed / Updates without speculative installs.

## CB-NX05 — Complete extension UX and settings

Integrate extension listing buttons (manual/Cinderbox/Vortex), browser click interception (opt-in), queue actions, download history, notifications, download destination, update checks, logs, reconnection status and fallback diagnostics. Cinderbox gets corresponding native settings and operational views in existing approved navigation. Preserve standalone Firefox operation and non-Cinderbox manager compatibility; avoid duplicating competing download services once paired.

## CB-NX06 — Full release qualification

Run combined fixtures and live acceptance on Firefox Android, Cinderbox Android 16/API 36, offline and unavailable-extension states, process death/recovery, Nexus auth/account-policy behavior, malicious/expired NXM, installation-review safety and UI visual fidelity. Hosted CI passes are not a replacement for real-device/Nexus account evidence. Keep all production release and automatic installation flags disabled until separately qualified.

## Sequencing and safety rules

**Strict order:** CB-NX01 first, then CB-NX02, CB-NX03, CB-NX04, CB-NX05, CB-NX06. Do not defer CB-NX01 in favor of larger queue work. Prior approved app UX work/qualifications remain historical and are not undone. Separate the integration lane from unrelated R2F/Shizuku PR #61. Never claim that this roadmap document itself constitutes any completed functionality.

**Sources:**

- Cinderbox merged NEX-R5: https://github.com/Mikeyphw/Cinderbox-Companion/pull/84
- Canonical Cinderbox UX roadmap: `design/cinderbox/04_ROADMAP/MASTER_ROADMAP.md`
- NEX-R5 implementation notes: `docs/devtool/NEX_R5_UNIFIED_DETAILS.md`
- Firefox extension source: https://github.com/Mikeyphw/scriptexts/tree/main/extensions/stardew-nexus-download-queue
