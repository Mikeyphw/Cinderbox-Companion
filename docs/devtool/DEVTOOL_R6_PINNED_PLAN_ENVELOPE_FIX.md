# R6 — pinned Devtool plan envelope (incremental on R5)

## Verified failure

PR #35 commit `3d37cb639924f391be878c307f1f37f77b54e83c`, workflow `Devtool source contract (no Gradle)` run `41366062345`, failed at its `Pinned A05/A07 config parser regression` step. The captured A05 `plan --json` **succeeded** but returned an outer Devtool machine envelope (schema_version 1) whose `data` field contained the valid planning response (schema_version 2, action `m24-verify-ux-check`, 2 nodes and nonempty commands). R5 incorrectly expected the inner plan at top level. This was a false-negative qualification test, not an Android build failure.

## Changes

- Added `scripts/devtool/pinned_plan_contract.py` to validate the **actual** nested Devtool CLI receipt and fail closed on `machine.operation.status != ok`, mismatched operation/workflow, target, or empty plan.
- Added six synthetic positive/negative tests and a source-only CI regression step.
- Replaced inline R5 JSON parser with the tested helper, retaining captured diagnostic printing on any failure.
- No changes to A05/A07 engine pins, signing, Gradle, Android app code, APK verification, or native device gates.

## Acceptance

Local offline checks prove only the helper, source contracts and overlay integrity. After applying/pushing R6 to the same feature branch, require PR source contract + Build Debug APK PASS and explicitly dispatch `devtool-android-build.yml` from the exact new commit for A05/A07 hosted plan, preflight and build evidence. Do not merge PR #35 based on offline tests alone. Check Android storage fix on a real device separately.
