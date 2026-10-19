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
