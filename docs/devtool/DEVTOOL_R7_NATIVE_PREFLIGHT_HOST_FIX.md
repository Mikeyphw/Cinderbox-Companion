# R7 — pinned A05/A07 real-host preflight correction (incremental on R6)

## Exact live evidence

GitHub workflow run `41368637387` (PR #35, feature-branch commit `ea5595e8b4ecb22e1a8f97e153af6dcf0615e477`) has two failed jobs: `A05 native DAG + EXO evidence` and `A07 installed-wheel native debug DAG`. Their captured artifacts show *successful* source-bound plans but *failed* `devtool preflight --workflow` responses: `section=environment`, `name=native-termux:termux`, `status=incompatible`, `detail=desktop-linux`, at the `security-contract` node.

The previous R6 config declared six source-only command jobs with `execution_environment = "native"`. **In both exact pinned Devtool releases** (`08eb13991b5d1c623b64fdd8f9524418ee27207e` and `409c5527532eaa1ee62b8111e030732d3f9e2791`), `native` is an alias for `native-termux`, **not** the current host. On GitHub's Ubuntu `desktop-linux` runners, this yields a preflight incompatibility before A05 or A07 can run. `host` maps to the detected current substrate on both Ubuntu and Termux, without chroot or Gradle. The security command and its source-signature bytes remain identical, retaining `PYTHONDONTWRITEBYTECODE=1`.

## Source changes

- Exactly six source-only host-check DAG command jobs now declare `execution_environment = "host"` (`security-contract`, `storage-alias-source`, `devtool-contract`, `a05-source-regression`, `a07-source-regression`, `a10-source-regression`).
- Offline configuration contract now **requires** `host` and refuses `native`, `auto`, or `desktop-linux` as non-portable execution choices for those jobs.
- Three regression tests cover all six jobs and fail closed against Termux-only and desktop-Linux-only regressions.
- No changes to signed APK source gates, developer signing pins, Android source, Gradle, CI workflows, or any device boundary.

## Acceptance boundary

This source-only overlay validator does NOT run the pinned Devtool engine, Gradle or the phone. Host platform mapping is confirmed by the pinned Devtool `execution_environments.py` contract, and original failure comes from GitHub artifacts. After applying/pushing the overlay, confirm PR #35 source-contract and debug-APK PASS, then **dispatch `devtool-android-build.yml` at the new exact feature commit** and inspect BOTH pinned preflight receipts for `data.healthy = true` plus downstream DAG execution. Preserve failure evidence; never declare remote A05/A07 success based only on green PR checks.
