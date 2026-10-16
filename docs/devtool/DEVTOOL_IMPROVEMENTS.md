# Persistent Devtool / Cinderbox improvements ledger

This ledger is cumulative; append future Devtool gaps and campaign findings rather than leaving them only in chat. Scope: `Mikeyphw/Cinderbox-Companion` Devtool overlay and test automation. Historical milestones remain acknowledged; none of their device evidence is reexecuted here.

| ID | Evidence / affected projects | Recommended change and rationale | Status |
|---|---|---|---|
| DEV-M19-PATH-001 | M19 first Android 16 `seedInterruptedDownloadCheckpoint` failed; Android system aliases such as `/data/user/0` can be symlink ancestors. Affects Cinderbox Android fixture base and source-bound Devtool tests. | Use reusable canonical app-private test fixture manager; retain strict production symlink rejection. | Implemented in M20; 52/52 Android device campaign PASS |
| DEV-M19-DIAG-002 | M19 initial `INSTRUMENTATION_INCOMPLETE_OR_FAILED` omitted actionable causes. Affects Devtool automation and Cinderbox source-bound device evidence. | Classify exceptions using fixed allowlist and Kotlin test line only; prohibit raw stack/path/token serialization. | Implemented and Android-qualified in M20 (52/52) |
| DEV-M19-FIXTURE-003 | An early failed M19 run may have left an isolated test directory; source runner had no inventory. | Persist cryptographically bound test-only ownership markers, ID-only inspection, explicit single-fixture cleanup with strict content verification; never bulk-delete user data. | Implemented in M20; ownership tests passed (device inventory cleanup remains opt-in) |
| DEV-M20-CASE-004 | Serial two-case Android campaigns cause repeated CI/device install cycles and risk incomplete result reporting. | One 52-case, eight-lane manifest; CI compile once, individually executable lanes and one source/provenance-bound consolidation, strict per-case totals. | Implemented, 52/52 M20 Android PASS |
| DEV-M20-SERVICE-005 | Production `GameDownloadService` has `START_NOT_STICKY`, coroutine jobs and connection to Steam; authenticated downloader cannot be safely tested under signed-out real-device fixture. | Preserve distinction between debug synthetic real Android foreground-worker lifecycle and actual Steam service. Future separately consented live-network integration required before stronger claims. | Explicit limitation / future work |
| DEV-M20-MERGE-006 | Multiple lane reports can otherwise be accidentally combined across APKs or PRs. | Reject source/CI/APK/device mismatch, overlapping lanes, missing test cases and absent genuine process-stop evidence; never infer release qualification. | Implemented, M20 consolidated 52/52 PASS |


### M20-IR-01 — Instrumentation teardown is not a worker-liveness receipt
- **Evidence:** PR #25 first Android run, CI `38917076629`, source
  `db985f5b0e19011a53b8911a3376c22ec53c53ec`: lanes A and B and C01–C07
  passed; pre-force-stop `pidof com.sdvsync` returned empty. No force-stop ran.
- **Affected:** `scripts/devtool/m20_qualification.py`; debug-only
  `M20SyntheticWorkerService`; genuine process-death evidence gate.
- **Improvement:** Re-arm and verify the non-exported synthetic foreground
  worker after instrumentation teardown, require live `ServiceRecord` and stable
  app PID, mark host-side lifecycle failures explicitly FAILED_OR_BLOCKED, and
  block force-stop if verification fails. Never substitute an
  Activity launch alone for proof of a running worker.
- **Status:** Re-arm confirmed on Android 16; lane C 8/8 PASS in PR #25.

| DEV-M20-G-UI-008 | Android 16 run at PR #25 `326d1045`, CI `38923143537`: G03/G05 both failed, while G01/G02/G04 passed. Test clicked passive Settings heading `Operation center` rather than the long CTA already qualified in M17. | Reuse M17's scroll-to navigation CTA; wait for Compose idle and confirm destination rendered before refresh. Preserve source-bound G-only retest. | Fixed and verified: M20 G/H 10/10 PASS, final consolidated 52/52 PASS |
| DEV-M20-DIAG-009 | The same failed run incorrectly reported `source_line:364` for both G03/G05 because instrumentation diagnostics searched the entire multi-case output, not the case's status event. | Group AndroidJUnitRunner events by `INSTRUMENTATION_STATUS_CODE` and matching test ID, classify only that event; retain allowlisted category/line, never publish raw stacks/paths. | Fixed and host-tested; M20 G/H 10/10 PASS, final 52/52 PASS |

### M21 — Consolidated actual-workflow and release-readiness campaign

| ID | Concrete evidence / affected projects | Recommended action / outcome | Status |
|---|---|---|---|
| DEV-M21-AUTH-010 | M20's 52 fixture-based scenarios do not exercise an actual authenticated Steam account and cloud metadata service. `SteamClientManager`, `SteamSessionStore`, `SteamCloudService`, `SteamContentService` are affected. | Require opt-in, non-mutating live Steam connection, encrypted session presence, license callback and cloud metadata enumeration. No raw secrets or user file names in reports; absence is BLOCKED rather than PASS. | Implemented M21 source/tests, CI/device pending |
| DEV-M21-LOG-011 | `SteamCloudService` previously emitted private cloud filenames, path prefixes, machine names and even decoded save text excerpts to application diagnostic logs. | Replace raw-value logging with aggregate transfer sizes/counts. Never emit batch IDs, raw cloud paths or save content. | Source change implemented; Kotlin CI pending |
| DEV-M21-APK-012 | M16 pinned the CI debug signer only. Existing release `keystore.jks` is separate and not automatically provisioned/qualified. A debug APK must not be labeled release-ready. | Enforce separately signed APK, independent APK and release-certificate pins, actual CI debug-signer comparison, verified package identity, and non-debuggable manifest. No signing keys in overlay or publication. | Implemented M21 release audit; real signed release artifact pending |
| DEV-M21-REAL-013 | M20 synthetic installation fixtures did not prove the presence of the actual Cinderbox Android package or that Companion's app-private data survives an explicit APK replacement. | Read PackageManager for actual `com.game.cinderbox`; require explicit opt-in, preserve a nonce-owned test marker across same-signer replacement and clean only that marker after success. Missing actual package is BLOCKED, not synthetic PASS. | Implemented M21 Android lane, real-device pending |
| DEV-M21-BOUND-014 | Repeating 74 completed M14–M20 device cases for new acceptance would obscure remaining unqualified areas and require unnecessary test cycles. | Separate 18-case versioned M21 matrix, reusable M14/M16 provenance/signature checks, independently executable lanes, one PR/one CI debug build, strict source/CI/APK/device merging. | Implemented M21 host/tooling, CI pending |
