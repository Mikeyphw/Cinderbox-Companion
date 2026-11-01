# R4: exact pinned-Devtool compatibility, branch-safe dispatch, Node24 native workflow

This hotfix is an **incremental overlay on R3**, not a standalone R3 replacement.
Source authority: `feature/m24-steam-download-safety` commit
`c1df599ba077734238132f2a9ab74f2f322d41e5` (PR #35).
Do not apply it to `master` or to an untouched R1/R2 checkout.

## Observed failure and correction

GitHub run `41361801792` failed at both A05 and A07 preflight with:
`Invalid wrapper configuration: wrapper.commands.ci-debug-plan contains unknown field(s): actions`.
The installed-wheel Devtool SHAs `08eb13991b5d1c623b64fdd8f9524418ee27207e`
and `409c5527532eaa1ee62b8111e030732d3f9e2791` cannot parse typed Actions wrappers.
R4 removes them from shared `.devtool.toml`. It does not upgrade/re-pin
A05/A07 or alter signed APK evidence/Android instrumentation workflows.

## New equivalent branch-aware operator CLI

The native Devtool Actions interface remains accessible with a narrow Python bridge:

```zsh
python3 -B scripts/devtool/hosted_debug.py plan
python3 -B scripts/devtool/hosted_debug.py run --yes
python3 -B scripts/devtool/hosted_debug.py watch --request-id YOUR_32_HEX_DEVTOOL_ID
python3 -B scripts/devtool/hosted_debug.py artifacts --request-id YOUR_32_HEX_DEVTOOL_ID
```

`plan`/`run` validate the active branch, clean local worktree and exact SHA
against GitHub before asking Devtool to plan/dispatch. `run` always requires
`--yes`; workflow/inputs/repository are fixed, debug-only and no local Gradle is used.
`watch`/`artifacts` accept only 32-char Devtool request IDs (not GitHub run numbers).
This requires an installed Devtool version that supports `devtool actions`.

## CI coverage

Source-only CI checks both old pinned Devtool parsers from **immutable commits**,
plans and preflights A05 and A07, runs Python regressions, and never invokes
Gradle/device/signing. Manual workflow upgrades its checkout/setup-java/
setup-android/Gradle/upload-artifact actions to reviewed, exact Node24 SHAs.
Legacy `build.yml` also switches **only its action refs** to reviewed Node24
SHAs. A10's canonical baseline is updated as an explicit action-only migration;
its immutable-source tests remain enabled and all Gradle, signing, APK naming,
release qualifications, and device gates stay as before. Hosted requalification
is required before accepting the new A10 baseline. Separate release candidate
workflows are not migrated under this hotfix.

## Acceptance

Run `./devtoolw host-check`, push the R4 commit, observe PR #35 source CI
and legacy Build Debug APK, and dispatch manual A05/A07 native workflow using
`gh workflow run devtool-android-build.yml --ref feature/m24-steam-download-safety ...`.
Do not merge until both A05 and A07 machine evidence are complete for the new SHA.
A successful hosted build does not establish a real-device storage fix.
