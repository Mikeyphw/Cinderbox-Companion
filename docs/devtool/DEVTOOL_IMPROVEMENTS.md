# Persistent Devtool / Cinderbox improvements ledger

This ledger is cumulative; append future Devtool gaps and campaign findings rather than leaving them only in chat. Scope: `Mikeyphw/Cinderbox-Companion` Devtool overlay and test automation. Historical milestones remain acknowledged; none of their device evidence is reexecuted here.

| ID | Evidence / affected projects | Recommended change and rationale | Status |
|---|---|---|---|
| DEV-M19-PATH-001 | M19 first Android 16 `seedInterruptedDownloadCheckpoint` failed; Android system aliases such as `/data/user/0` can be symlink ancestors. Affects Cinderbox Android fixture base and source-bound Devtool tests. | Use reusable canonical app-private test fixture manager; retain strict production symlink rejection. | Implemented in M20, device qualification pending |
| DEV-M19-DIAG-002 | M19 initial `INSTRUMENTATION_INCOMPLETE_OR_FAILED` omitted actionable causes. Affects Devtool automation and Cinderbox source-bound device evidence. | Classify exceptions using fixed allowlist and Kotlin test line only; prohibit raw stack/path/token serialization. | Implemented M20 host tests, device qualification pending |
| DEV-M19-FIXTURE-003 | An early failed M19 run may have left an isolated test directory; source runner had no inventory. | Persist cryptographically bound test-only ownership markers, ID-only inspection, explicit single-fixture cleanup with strict content verification; never bulk-delete user data. | Implemented M20, Android validation pending |
| DEV-M20-CASE-004 | Serial two-case Android campaigns cause repeated CI/device install cycles and risk incomplete result reporting. | One 52-case, eight-lane manifest; CI compile once, individually executable lanes and one source/provenance-bound consolidation, strict per-case totals. | Implemented M20 host checks, device qualification pending |
| DEV-M20-SERVICE-005 | Production `GameDownloadService` has `START_NOT_STICKY`, coroutine jobs and connection to Steam; authenticated downloader cannot be safely tested under signed-out real-device fixture. | Preserve distinction between debug synthetic real Android foreground-worker lifecycle and actual Steam service. Future separately consented live-network integration required before stronger claims. | Explicit limitation / future work |
| DEV-M20-MERGE-006 | Multiple lane reports can otherwise be accidentally combined across APKs or PRs. | Reject source/CI/APK/device mismatch, overlapping lanes, missing test cases and absent genuine process-stop evidence; never infer release qualification. | Implemented in M20 host suite, device qualification pending |


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
- **Status:** Source correction implemented; new CI and real-device verification pending.

| DEV-M20-G-UI-008 | Android 16 run at PR #25 `326d1045`, CI `38923143537`: G03/G05 both failed, while G01/G02/G04 passed. Test clicked passive Settings heading `Operation center` rather than the long CTA already qualified in M17. | Reuse M17's scroll-to navigation CTA; wait for Compose idle and confirm destination rendered before refresh. Preserve source-bound G-only retest. | Fixed in M20 targeted overlay; new CI/device check pending |
| DEV-M20-DIAG-009 | The same failed run incorrectly reported `source_line:364` for both G03/G05 because instrumentation diagnostics searched the entire multi-case output, not the case's status event. | Group AndroidJUnitRunner events by `INSTRUMENTATION_STATUS_CODE` and matching test ID, classify only that event; retain allowlisted category/line, never publish raw stacks/paths. | Fixed in M20 targeted overlay; host tests added, device verification pending |

### M21-CI-SDK-015 — Release verifier masked Android SDK tool discovery failures
- **Evidence:** `Mikeyphw/Cinderbox-Companion` release candidate GitHub Actions run
  `38960889421`, workflow commit `8a0d733a1553c57186907e8847010f559da737e6`;
  release keystore/certificate provisioning PASS, `:app:assembleRelease` PASS (53
  tasks), but verification emitted `M21_RELEASE_APK_SIGNATURE_INVALID`, hiding
  whether `apksigner` was absent or cryptographic verification actually failed.
- **Affected:** `scripts/devtool/m21_actions_release.py` and release candidate
  workflow; `android-actions/setup-android` does not promise pinned build-tools
  binaries are in PATH, while M16 already had SDK-directory fallback.
- **Improvement:** Resolve both `apksigner` and `aapt` from the explicitly
  installed `$ANDROID_HOME/build-tools/35.0.0/` (or `ANDROID_SDK_ROOT`);
  use PATH fallback only for local runs without an SDK root; report distinct
  fail-closed unavailable-tool errors without exposing credentials. Preserve
  real signature, independent release cert, package and debuggability checks.
  Add host regression coverage for pinned-tool selection and missing binaries.
- **Status:** Fix implemented and nine focused host tests PASS; new CI and a
  real signed APK verification required. The original failure cause is not
  definitively confirmed until the corrected verifier executes in Actions.
