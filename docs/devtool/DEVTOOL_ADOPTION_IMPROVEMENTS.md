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
