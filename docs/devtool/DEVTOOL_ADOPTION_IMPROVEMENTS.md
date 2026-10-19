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
