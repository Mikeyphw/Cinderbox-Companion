# CB-NX06 LAB03C — Deliberate exact-file page action (source implementation)

**LAB03B physical pairing / Iceraven UX09 acceptance is deliberately DEFERRED**, not waived or passed. This overlay implements the next source milestone only. It never automatically installs, signs, merges, downloads, opens a live browser, or touches production Mods/game data.

## Behavior

- Existing LAB private inbox admission remains an HTTP *request*, not download authority.
- First Android LAB tap opens an **in-app confirmation dialog**, not a browser.
- Confirmation displays the exact mod ID and file ID, with an explicit warning that a `file_id` query parameter is only a **page hint**. Actual file selection, Nexus login, and provider requirements remain manual and unverified.
- The confirmation handler re-reads the app-private inbox on the second tap and checks ID and `PENDING` status again. Requests older than ten minutes, with future clocks or invalid numeric identities, fail closed. Existing pending entries are not silently deleted.
- The LAB browser launcher only accepts the exact `https://www.nexusmods.com/stardewvalley/mods/<mod>?tab=files&file_id=<file>` shape and an installed supported Firefox/Iceraven browser. **No `nxm://` or Cinderbox-specific deep link is emitted in LAB.** A missing browser refuses; there is no generic Android chooser fallback to an NXM manager.
- `OPENED` inbox status is written only **after Android accepts the explicit `ACTION_VIEW` launch request**. This does not establish that Nexus loaded, that a file was authenticated or downloaded, or that any file bytes were staged. If the browser launch fails, the request remains pending.
- Production `com.sdvsync` retains the pre-existing NXM flow, consent UI and endpoint `38471`. LAB stays `com.sdvsync.cbnx06lab` with private file roots, port `38472`, and no privileged storage, Steam or auto-install behavior.

## Gates

- New pure Kotlin `NexusLab03CPolicy` plus JVM regression tests for exact IDs, expiry and official URL safety.
- Source mutation negatives for second-tap confirmation, inbox read-back, expiry, browser dispatch refusal, no NXM, and honest labels.
- New hosted workflow performs the source/negative suite, `:app:testDebugUnitTest` and `:app:assembleCbnxLab`; the existing full LAB workflow also runs the gates. Gradle **only via GitHub Actions**.
- All hosted results are **source-only**, not a physical or Nexus authorization witness. Browser UX09 scroll/pairing and LAB03B before/after tests remain pending independent acceptance.

## Later, only after separate physical authorization

1. Validate installed LAB APK bytes and new source SHA; don't replace production.
2. Pair the isolated Iceraven LAB extension to port `38472` after user consent; capture LAB03B read-only before/after evidence.
3. For LAB03C, see a new exact inbox request, tap **Review file page (LAB)**, verify the confirmation dialog, cancel first and ensure no launch, then confirm one fresh request. Observe that only a Nexus HTTPS files page opens; verify actual Nexus identity/requirements manually.
4. Record redacted app/browser evidence; revoke pairing. Do not infer download, archive provenance, game immutability or release readiness.

Next: LAB03D explicitly authorized private archive staging and checksum, LAB04 lab-only synthetic install/rollback, LAB05 UI E2E, LAB06 physical acceptance, CB-NX07 release review. No automatic merge/release.
