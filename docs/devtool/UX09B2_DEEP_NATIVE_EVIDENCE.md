# UX-09B2 — Actual offline deep-route screenshot evidence (21/24)

Source-pinned base: `393f9ae7ef279ae4bfc9eab841b9ac2506cef1b5` (merged UX-09B PR #71).

## Adds

- Four independent `createAndroidComposeRule<MainActivity>()` real-activity captures: Download queue (from Mods), File access (from More), Operation center (from More), Installation health (from More).
- A single API36 hosted emulator run reruns all 17 UX-09B captures and then captures these four routes using the same APK pair, CI run ID, and source SHA.
- Four HTML-vs-Compose tri-pane difference images, measured diagnostic RGB differences, hashes and JSON receipt. Coverage grows from **17 to 21 of 24** actual native screens, while source safety gates and zero-release policy persist.

## Explicitly NOT proven

- The remaining **three reference states**: `game-steam-connected-393`, `saves-cloud-connected-393`, and `mod-detail-393` require strictly isolated test-only deterministic state injection; no real user Steam/entitlement/Nexus credentials or mod files may be consumed.
- The HTML reference contains demonstrative data; the native app is an empty, local-first hosted emulator. Pixel parity is **not approved**. Do not turn screenshot differences into a pass by weakening thresholds. Native goldens remain unapproved.
- Production repair, file moves, privileged provider access, Shizuku, root, release publication, automatic installs, and physical-device acceptance remain untouched/gated.

## Next UX-09B work

Build explicit DI-only synthetic fixture providers for remaining three render states, with production source never accepting synthetic authorization as a download/cloud permission. Then finish anchor/inset contracts, align truly discrepant Compose layout with approved single-dark HTML, and have native goldens independently approved. UX-09C 200% text/accessibility and lifecycle qualification follows UX-09B.
