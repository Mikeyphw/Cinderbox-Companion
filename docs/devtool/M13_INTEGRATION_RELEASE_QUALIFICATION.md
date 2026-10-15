# M13: Integration and qualification evidence (NOT a release)

M13 adds reproducible cross-feature JVM tests, source-to-consumer checks, CI/APK
fingerprint linkage, a sanitized CI-result assessor and an optional non-mutating ADB
observation. It **does not** enable publishing, convert a debug APK into a release,
auto-install an APK, or claim real-device functional qualification.

## Automated build gates

- Verify recovery-producing modules (download, mod profiles, batch install, game
  repair, save restore) remain connected to the Operation Center and their existing
  recovery consumers. Reject drift and unsafe navigation.
- Run M13 JVM integration tests alongside the existing per-milestone M3–M12 tests.
  The tests exercise journal coexistence, corruption isolation and status aggregation.
- During debug CI, compare the M3 APK source/provenance to the exact checked-out
  commit, APK bytes, and observed signature metadata. The M3 record is a CI **self-report**;
  M13 does not claim independent attestation or reproducibility.
- Upload `M13_QUALIFICATION.json` alongside `M3_PROVENANCE.json` and the debug APK.
  All release/device fields remain blocked/NOT_RUN, even on successful CI.

## CI run validation (after GitHub Actions completes)

```sh
# From the checked-out commit of the workflow run:
bash scripts/devtool/m13_collect_ci.sh RUN_ID [OUTPUT_DIR] [TRUSTED_COMMIT_SHA]
```

Uses `gh api` to obtain run and job-step status and verifies an explicitly trusted source SHA (by default local HEAD, or the optional third argument for a PR merge commit),
repository, debug workflow, successful complete job and required stage names.
Never accepts incomplete, canceled, skipped, or wrong-commit runs. `M13_CI_QUALIFICATION.json`
is local observation, not attestation. The JSON may be provided to another evidence system
but contains no raw logs or account information.

## Optional read-only device observation

```sh
python3 scripts/devtool/m13_qualification.py device \
  --output "${TMPDIR:-/tmp}/M13_DEVICE_OBSERVATION.json"
```

Requires exactly one authorized ADB target; reads platform properties and whether
`com.sdvsync` is present via `pm path`. Outputs neither serial nor APK path. No
installation, root access, app launch, or private data inspection. **A successful
observation does not count as functional testing**. The existing explicit
`./devtoolw device` lane can separately run Android instrumentation, but can install
an APK and is not run by M13 automatically.

## Production eligibility

`docs/security/M3_RELEASE_POLICY.json` still blocks production release and publication.
The separate M3B *signed candidate* feature may be configured with a pinned cert,
but is explicitly non-publishing and not a qualified production release. Independent
real-device upgrade/rollback testing, source attestation, signing approval, and
reviewed release policy changes remain prerequisites. Do not label NOT_RUN as a test
failure, and do not treat a green CI workflow as release authorization.

## Evidence classifications

- `PASS` / `PASS_*` means the named automation explicitly observed the check.
- `NOT_RUN` means the check has not been executed with relevant evidence.
- `BLOCKED_BY_POLICY` means production release remains disabled, even if a
  manually invoked signed-candidate lane has a pinned certificate.
- A failure produces a nonzero exit and no success JSON; it never yields a
  `qualified_release=true` field.
