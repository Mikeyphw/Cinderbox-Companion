# CB-NX06 LAB03A HF03 — Correct AndroidJUnitRunner result semantics

Pinned parent: `1b68d754f7abba34632ea879b6536dc898983fb4` (Cinderbox PR #89).

**Confirmed source defect:** Both the legacy and per-case receipt parsers treated `INSTRUMENTATION_CODE: 0` as a successful instrumentation run. Android's AndroidJUnitRunner uses the *final* `INSTRUMENTATION_CODE: -1` for `Activity.RESULT_OK`; this differs from an individual passing `INSTRUMENTATION_STATUS_CODE: 0`. The incorrect check could unconditionally reject passing runs. HF03 corrects the final code in both parsers, source gate and inherited positive fixtures. It adds explicit successful/mismatched final-code, failed-case, negative-status and aggregate-two-cases regression tests.

HF03 does NOT delete or skip either Android test, change target package, change 38472/38471 ports, alter APK/install scope or adjust private data boundaries. The running emulator still must execute both real tests and output a PASS for each. Prior HF02 artifact's exact case failures could not be retrieved; therefore correcting this confirmed defect is **not** evidence of runtime qualification. Inspect the new exact-SHA hosted receipt and logs. If either case fails, STOP before LAB03B and diagnose the next failure.

The launcher uses a disposable `$TMPDIR` clone, checks exact PR SHA and Git blob IDs, refuses drift, changes only its 4-file allowlist, runs inherited source/negative suites, commits with the pinned parent, non-force pushes only the existing PR branch and verifies remote Git objects. It never touches the user's permanent checkout or physical Android/device/browser/game. `--offline-test` is local-only, and `--resume-only` is read-only PR tracking.
