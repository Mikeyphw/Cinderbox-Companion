# A10 — Consolidate native and legacy CI lanes (safe first cut)

Source baseline: `cb218cbae3e5eed5769ba784dd5d1fc747f40dd1`.

## Current behavior

- **Manual dispatch defaults to native**: `a05_mode=native-only`, `a07_native_build=true`.
  A07 uses the frozen installed A06 wheel, Devtool's native
  `security-contract → debug-apk → verify-debug-apk` DAG, the M16 debug signer,
  M3/M13 provenance and source/run-bound machine artifacts. A05 source DAG
  continues independently, and the legacy build is skipped.
- **Legacy fallback is explicit**: choose `a05_mode=off` and
  `a07_native_build=false`. The dispatch's legacy job delegates to
  `.github/workflows/build.yml` through `workflow_call` and `secrets: inherit`,
  not a copy of 300+ Gradle/security/testing steps. A guarded fallback-only
  packaging step retains `devtool-android-debug-apk` with its SHA256SUMS,
  BUILD_INFO and independently regenerated M3/M13 evidence, in addition to
  the existing standard `debug-apk` artifact. `a05_mode=both` retains the
  historical legacy + A05 source-DAG mode; A07 runs only in `native-only` mode.
- **A05 source-only**: choose `a05_mode=native-only` and
  `a07_native_build=false`. No APK build runs.
- **Automatic push/PR CI stays unchanged**: `build.yml` retains its original
  full M3–M24 host regression, stable signer, debug APK and instrumentation APK
  gates. Its original source/build/test steps are unchanged; the additions are
  `workflow_call:` and the fallback-only Devtool artifact staging.
  This protects branch checks while the default native manual lane receives
  further hosted and negative acceptance. No existing branch protection or
  required check is deleted or renamed.

## Dispatch

```sh
# Native default; explicit values shown for auditable replay
gh workflow run devtool-android-build.yml --repo Mikeyphw/Cinderbox-Companion \
  --ref feature/m24-steam-download-safety \
  -f project_dir=. -f module=app -f variant=debug -f format=apk \
  -f a05_mode=native-only -f a07_native_build=true

# Explicit fallback: full legacy build and its existing artifacts
# This is a separate run, never an automatic retry after a native failure.
gh workflow run devtool-android-build.yml --repo Mikeyphw/Cinderbox-Companion \
  --ref feature/m24-steam-download-safety \
  -f project_dir=. -f module=app -f variant=debug -f format=apk \
  -f a05_mode=off -f a07_native_build=false
```

## Acceptance before migrating automatic CI to native

1. Inspect a new native-default dispatch: A07+A05 succeed; the single delegated
   legacy job is skipped; A07 `verify-run` validates the exact SHA, attempt,
   signer, receipts and APK bytes. The previously accepted A07 run remains
   historical evidence, not automatic proof for the new workflow revision.
2. Exercise one **explicit** legacy-fallback dispatch: reusable `build.yml`
   produces the expected `devtool-android-debug-apk`, M3/M13 evidence and
   instrumentation artifacts. Verify its real run and source identity.
3. Keep the automatic `Build Debug APK` push/PR workflow green, including
   source regressions and instrumentation APK, for the same candidate commit.
4. Only after those distinct gates pass consider replacing the push/PR default
   builder with native Devtool. Do not drop full source/instrumentation coverage
   or an existing required status check to create an illusion of consolidation.

## Qualification boundary

No automatic release publication, device install/uninstall, source attestation,
production signing, device qualification or equivalence of APK bytes. Existing
A05/A07 historical receipts and source pins remain unchanged. The canonical
legacy workflow is retained as a manual fallback; no silent fallback from a
failed native lane.

## Legacy source-check migration

A10 also updates existing M3–M24 source assertions. Their previous wording
assumed the same regression steps were copied inside both YAML files. The new
`ci_workflow_contract.effective_ci_source` validates one exact, read-only,
repository-local delegation, then resolves the canonical legacy test steps.
It preserves and compares the original standard CI body SHA-256, and fails
closed on missing or altered signing steps, false target paths, symlinks or
changed artifact layout. All raw tracked source digests remain independent.
It must never be interpreted as proof that the smaller native A07 DAG itself
executes every full legacy test or instrumentation scenario.
