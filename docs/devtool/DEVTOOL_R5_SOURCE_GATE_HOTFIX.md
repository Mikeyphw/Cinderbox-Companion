# Cinderbox R5 — source-only pinned Devtool plan gate hotfix

## Evidence

PR #35 R4 commit `2a932f30875852269041c2aa9be0fbb7210e222e`:
- `Build Debug APK` run `41363562082`: PASS.
- `Devtool source contract` run `41363562164`: FAIL, solely at the new pinned A05/A07 parser step; all earlier jobs in that workflow passed.
- The pinned Devtool CLI `plan --json` returns schema version 2 with `action`, `targets`, `summary`, `graph`, and `commands`. `preflight --json` returns a separate `healthy`-based toolchain report. R4's new test checked an unrelated `ok/machine.operation.status` shape for BOTH, guaranteeing failure even when planning succeeded; redirecting all JSON to a temporary file also concealed root-cause errors. The hosted log does not by itself distinguish this assertion failure from an earlier hidden command failure, so that distinction remains to be verified by the next run.

## Changes

- R5 corrects the parser assertion to check the actual pinned `plan` schema (`schema_version=2`, action, target and nonempty executable graph/command list).
- A failure to plan prints the exact command's captured JSON/error text to GitHub Actions logs.
- Removed SDK-dependent `preflight` from the **source-only** test job (it lacks JDK/SDK by design); no actual Android build or toolchain gate is bypassed. A05/A07 native hosted jobs continue to run their own plan and preflight with appropriate environments.
- Does not modify Devtool pins, Android code, Gradle workflow, signing, APK verification, wrapper, or runtime permissions.

## Qualification limits

Offline Python/source tests and YAML/shell validation cannot prove hosted pinned plan success. After committing R5 to the same feature branch, require the source-only PR workflow to pass. Then explicitly dispatch `devtool-android-build.yml` on the same SHA and inspect A05/A07 complete evidence. Do not merge on source-only evidence alone.
