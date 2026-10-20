# Devtool consumer adoption improvements — cumulative

Keep this ledger alongside Cinderbox adoption. The main Devtool-wide ledger is
`Mikeyphw/devtool/docs/DEVTOOL_IMPROVEMENTS.md`; this consumer record should
be reconciled into it in the next Devtool-core overlay. Do not rewrite history.

## 2026-10-19 — ACTIONS-A05 native consumer gate

- **Evidence:** A04 native source `08eb13991b5d1c623b64fdd8f9524418ee27207e`;
  Cinderbox source `ebac91b1deb7da65aa2905e3d75e1825a5ec4097`;
  existing `devtool-android-build.yml` with extensive source and APK steps;
  target-local `security-contract` → `m24-verify-ux-source` DAG.
- **Gap:** ACTIONS-A03 created reviewable generated workflows, but Cinderbox
  already had a registered Android build workflow; duplicate workflows would
  fragment EXO/run provenance and inadvertently rerun release-signing steps.
- **Recommendation:** Adopt **opt-in**, independent source-only DAG jobs on
  established workflows, keyed to pinned Devtool commits. Retain explicit
  `run_id`/`attempt`/source hashes and fail-closed artifact re-verification.
- **Affected:** Cinderbox, Devtool ACTIONS-A03/A04, future Android consumers.
- **Status:** Source implementation/automated local tests; live GitHub job and
  artifact qualification **OPEN** until exact-run remote receipt passes.
- **Open Devtool issue:** A04 self-update repository-local run-catalog
  persistence remains unresolved; external XDG state isolation is a workaround,
  not formal closure. Independently reported GitHub 404 requires exact resource
  identification; `--auth gh` repository/workflow diagnosis already passed.

## 2026-10-19 — A05-R1: GitHub wheel schema omission (LIVE-A05-01)

- **Observed remote evidence:** workflow run `39296491876` at Cinderbox commit
  `b7559c0277f34e3ada9638ef605b6af68ec658ee`, attempt 1,
  job `118210275751` and artifact `12208156319`.
- **Root cause:** pinned Devtool A04 successfully cloned and built its wheel,
  but the wheel excluded `devtool/core_cli_schema.json` even though
  `devtool/core_parser.py` requires it at module import. The first DAG plan
  aborted with `FileNotFoundError`; later preflight/invoke did not run.
- **Consumer mitigation:** import the exact hash-verified Devtool source checkout
  using `PYTHONPATH` inside each CI step, and assert origin and canonical
  schema presence before invoking anything. Retain the pinned venv to install
  dependencies; no floating branch or remote dispatch replay.
- **Affected:** Cinderbox source-only GitHub A05 workflow and Devtool Python
  wheel distribution; other installed-wheel consumers potentially affected.
- **Producer action OPEN:** add `core_cli_schema.json` to Devtool
  `pyproject.toml` setuptools package-data; build wheel and **test CLI from an
  installed wheel outside the source tree**, preserving JSON schema identity.
- **Disposition:** first GitHub run FAILED, artifact incomplete and correctly
  unqualified. Cinderbox A05-R1 local source acceptance pending, live rerun
  pending. Nothing is release/device qualified.

## 2026-10-19 — A05-R2: GitHub omits workflow_dispatch inputs + machine-file envelope (LIVE-A05-02)

- **Observed live evidence:** run `39301086093`, attempt `1`, Cinderbox commit
  `7675f3471326b3ca52a9474a17d96a6bde2943d6`; native DAG job
  `118226159093` **success**, Android build job `118226161404` **skipped**;
  artifact `12211842809`, name `cinderbox-a05-native-dag`, SHA-256 ZIP digest
  `f21e550f4a632a492a4f73e07a75859d01394a63173d68f832bd354fd86671ea`.
- **Defect A:** GitHub's actual workflow-run REST document omits `inputs`
  entirely. The verifier incorrectly treats absence as a proven mismatch.
- **Defect B:** `invoke --machine-file` emits `ok`, `exit_code`, EXO machine
  operation state and failure counters; unlike `plan/preflight --json`, it
  does not contain `result.success`. The verifier wrongly required it.
- **Repair:** if dispatch inputs are genuinely absent, examine job conclusions
  **only after verifying the immutable workflow at that exact run's source
  commit contains the mutually constraining mode guards**. Explicitly present
  contradictory inputs still refuse. For `native-only`, require A05 job success
  and Android build skipped; for `both`, both jobs must succeed. Recognize the
  canonical invoke envelope and fail closed on missing/failed operation and
  any nonzero failure counters. Keep internal SHA256SUMS, run attempt, source,
  artifact identity and remote conclusion requirements intact.
- **Affected:** Cinderbox A05-R1 remote verifier, future GitHub Actions
  consumers of Devtool machine-file; no change to CI execution or signing.
- **Qualification:** GitHub run success and downloaded artifact bytes checked;
  formal user-local `PASS_CINDERBOX_A05_GITHUB_RUN_VERIFIED` receipt pending
  A05-R2 installation. Device/release qualifications remain false. Separate
  Devtool-core wheel packaging repair remains OPEN.


## ACTIONS-A07 — Native installed-wheel host debug build (2026-10-19)

- **Evidence:** Cinderbox A05's hosted DAG passed after a temporary source-checkout workaround. Producer A06 commit `409c5527532eaa1ee62b8111e030732d3f9e2791` packages `core_cli_schema.json` in the installed wheel; local A06 acceptance was independently reproduced (3 tests, no skips). Hosted wheel smoke was still open when A07 was prepared.
- **Affected consumers:** Cinderbox-Companion; reusable pattern for Skybind, Studyflow and other adopters after acceptance.
- **Improvement:** Add an opt-in A07 job to the registered Android workflow invoking existing `security → debug APK → verify` native Devtool DAG using a pinned A06 installed wheel; retain M16 debug signer, M3/M13 provenance, SHA256, separate run/attempt artifacts and fail-closed verification. Preserve the existing A05 job and legacy Android job; A07 requires A05 native-only mode to skip the legacy build.
- **Compatibility:** Existing M3 dispatch source gate expected two option lists and rejected previously reviewed A05 `a05_mode`. Accept exactly that reviewed third list while rejecting any other choice expansion. This is not a release permission change.
- **Status:** Prepared overlay; local source acceptance, native host GitHub qualification, Android device qualification and release qualification tracked separately. Do not equate a prepared overlay or local tests with successful GitHub hosted build.


## ACTIONS-A07-R1 — Invalid GitHub job-level runner context (2026-10-19)

- **Evidence:** `gh workflow run devtool-android-build.yml` returned HTTP 422 at line 422, column 24: `Unrecognized named-value: 'runner'`. Commit `e29d1b030167e302245467e30152b0043496ea6a` uses `${{ runner.temp }}` in `jobs.a07-native-debug-build.env`, where the runner context is unavailable.
- **Affected projects:** Cinderbox-Companion A07 host APK CI; reusable Devtool Actions overlay workflow-authoring checks.
- **Repair:** Move the isolated `DEVTOOL_XDG_DIR` path into each consuming **step-level** `env` block (plan/preflight and invoke). Keep the same expression and state path at supported scope. Preserve A05, legacy build, pinned A06 wheel, debug signer, evidence and release/device boundaries. Add executable negative regressions to A07 source contract so job-level runner context fails before GitHub dispatch.
- **Status:** Repair overlay prepared; local/source and hosted validation tracked separately. Do not claim A07 GitHub qualification until a new run and exact-run artifact verification pass.

## ACTIONS-A07-R2 — Retired Android SDK `tools` package in setup-android@v3 (2026-10-19)

- **Evidence:** GitHub Actions run `39332329245`, attempt 1, source `1e680418385b3fb5f3e36bc333a2e9fbdd13f1fd`, A07 job `118333307284`: checkout and A07 source validation succeeded, but `android-actions/setup-android@v3` invoked `sdkmanager tools` and failed `Warning: Failed to find package 'tools'` (exit 1). A05 independently passed. No A07 debug APK was generated. This is an upstream obsolete SDK package default, not an APK/signing failure.
- **Affected projects:** Cinderbox-Companion A07 native debug build; Devtool Actions adoption generator and reusable workflow source validation.
- **Repair:** In the A07 SDK setup step, explicitly request `with: packages: platform-tools`, retaining existing `android-actions/setup-android@v3` and separately pinned compile SDK/build tools. Add fail-closed source-contract validation and negative tests for omitted or retired SDK packages. Preserve previously qualified A05, M16 signer, A06 wheel pin, M3/M13 evidence, device and release boundaries.
- **Preventive recommendation:** Implement source-bound GitHub Actions checks for removed Android SDK packages (and job/step expression scopes) before dispatch; update generated workflow templates to avoid deprecated defaults. Review other setup-android@v3 consumers without altering them automatically.
- **Status:** R2 repair prepared and locally validated; GitHub-hosted A07 APK and exact-run artifact qualification pending a new run. Do not treat the failed run as qualification.


## 2026-10-20 — A10 duplicate legacy CI body + native-default ergonomics

- **Evidence:** Cinderbox commit `cb218cba` had an extensive `build.yml`
  push/PR APK workflow and a second, copied legacy full build job inside
  `devtool-android-build.yml`; A07's hosted native DAG had already passed
  run `39336899057`, but a new manual dispatch defaulted to the legacy job.
- **Impact:** duplicated Gradle tests/build/signing configuration could drift;
  the native path was not the normal manually dispatched path.
- **Fix (source-stage):** add `workflow_call` to the existing, unchanged push/PR
  workflow; dispatch delegates its fallback via a reusable job, selecting
  native A07+A05 by default. Preserve manual fallback, source gates,
  existing APK/instrumentation artifact names and minimal read-only permissions.
- **Acceptance:** local source/negative checks before push; new exact-commit
  native-default and reusable legacy-fallback hosted run acceptance remain OPEN.
  Full push/PR default migration is DEFERRED until parity and required
  regression/instrumentation gates are demonstrated on the revised source.
- **Status:** SOURCE_TESTED_ONLY; preserve all earlier A05–A07 receipts.


### A10 source-contract reconciliation (same root cause)

- **Evidence:** M13/M16 and M5–M24 source checks historically asserted that
  complete M3–M24/instrumentation steps appeared in **both** YAML files. Real
  source deduplication therefore initially refused, despite the canonical
  `build.yml` retaining its steps. M3G also depended on the old Gradle
  command's exact textual formatting.
- **Resolution:** add `ci_workflow_contract.py`, verifying the exact delegated
  same-repository job, source-bound unchanged legacy CI body, signing/artifact
  handoff and native default; project only the canonical legacy branch to the
  existing milestone *source* checks. Preserve raw source digests independently.
  M13/M16 separately verify native debug, signer and release-policy boundaries.
- **Limits:** source tests do NOT claim that A07 executes all legacy milestone
  regressions; automatic push/PR and explicit fallback continue doing so.
  Kotlin-heavy M24 synthetic proof and the first revised GitHub runs remain
  additional acceptance. No silent native failure → legacy re-dispatch.
- **Status:** LOCAL_CONTRACT_VERIFIED; REMOTE_ACCEPTANCE_PENDING.

## 2026-10-20 — ACTIONS-A10 executable-mode overlay regression

- **Evidence:** Native A10 rehearsal on the exact `cb218cba` Cinderbox tree passed source tests and auto-commit, but the initial overlay ZIP demoted `scripts/devtool/m24_provenance_gate.py` from Git mode `100755` to `100644`, even though its content checksum still matched.
- **Impact:** Reusable CI source checks could remain green while direct script execution lost the executable bit. This is an overlay ZIP packaging issue, not a reason to weaken source qualification.
- **Correction:** Emit POSIX file modes from the frozen Git source in native ZIP entries; validate the executable gate and compare all affected paths' post-commit modes with their parent. Rehearse the full native apply again before installation.
- **Status:** corrected in A10 bundle; hosted GitHub acceptance remains outstanding.
