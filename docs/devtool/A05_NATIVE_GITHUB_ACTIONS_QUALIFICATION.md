# ACTIONS-A05 — Cinderbox native Devtool DAG evidence pilot

## Scope

The existing `.github/workflows/devtool-android-build.yml` remains the registered
workflow. Its established debug APK, debug signing, Gradle, CI artifact and
source gates remain unchanged **by default**. The new `a05_mode` dispatch
input has three explicitly different behaviors:

- `off` (default): run the existing build job, do not run A05.
- `native-only`: skip the existing build job and run only the source-only A05 DAG.
- `both`: run the existing Android build plus independent source-only A05 DAG.

A05 executes pre-existing target-local `m24-verify-ux-check` (security contract
→ M24 verification UX/folder picker), via Devtool plan, preflight and invoke.
It adds only the `a05-check` wrapper alias. It does **not** perform Steam
operations, Android instrumentation, app install, signing or publication.

## Frozen identities

- Cinderbox parent: `ebac91b1deb7da65aa2905e3d75e1825a5ec4097`.
- Devtool source: `08eb13991b5d1c623b64fdd8f9524418ee27207e` (A04 accepted).
- Host: `ubuntu-24.04`. No root/Android/device tokens or privileged writes.
- Checkout and upload-artifact Actions pinned to full Git SHAs in the A05 job.
- Evidence artifact: `cinderbox-a05-native-dag`, retained 14 days.

The evidence includes the exact GitHub `run_id` and `run_attempt`, consumer
`GITHUB_SHA`, Devtool SHA, canonical plan/preflight/invoke machine JSON and a
SHA256SUMS manifest. Collection occurs even when DAG execution fails. The
verifier refuses to mark missing, failed or mismatched evidence successful.

## Run after source merge or branch push

The workflow must be present on GitHub at the selected ref. Using the
feature branch from this snapshot, run:

```sh
gh workflow run devtool-android-build.yml \
  --repo Mikeyphw/Cinderbox-Companion \
  --ref feature/m24-steam-download-safety \
  -f project_dir=. -f module=app -f variant=debug -f format=apk \
  -f a05_mode=native-only
```

Observe the exact run with `gh run list --repo Mikeyphw/Cinderbox-Companion
--workflow devtool-android-build.yml --branch feature/m24-steam-download-safety
--limit 5`. Then verify **one explicitly selected run and commit**:

```sh
python3 scripts/devtool/a05_actions_qualification.py verify-run \
  --run-id YOUR_RUN_ID --sha YOUR_EXACT_CINDERBOX_HEAD_SHA \
  --mode native-only --out "$HOME/cinderbox-a05-YOUR_RUN_ID"
```

For a combined Android build plus A05, dispatch `a05_mode=both` and verify
with `--mode both`. The verifier requires both GitHub jobs to succeed in this
mode. Do not interpret the source-only job as Android-device qualification.

## Acceptance boundaries

A local receipt from `python3 scripts/devtool/a05_acceptance.py` records source
and tests **only**. It cannot create an external GitHub run or qualify the
Android APK, device, user sign-in or release. These are separate obligations.
Remote verification only succeeds after exact-run, attempt, source and checksum
verification. No credential values or private application data enter the
A05 evidence artifact.

## Troubleshooting

If a workflow's resource is not accessible, distinguish `gh auth status`,
`gh api repos/Mikeyphw/Cinderbox-Companion`, `gh workflow list`, and the
selected exact run. The generic GitHub 404 is not evidence that all repository
access is broken. Inspect the selected workflow and ID before redispatching.

## A05-R1: source-runtime repair after actual GitHub attempt

The initial GitHub run [39296491876](https://github.com/Mikeyphw/Cinderbox-Companion/actions/runs/39296491876)
failed after installing frozen Devtool A04: its wheel omitted the canonical
`core_cli_schema.json`. The first plan step could not import Devtool. The
existing uploader correctly archived an **incomplete** result; that attempt
MUST NOT be qualified or rerun as an unchanged source.

A05-R1 retains the Devtool source SHA `08eb13991b5d1c623b64fdd8f9524418ee27207e`.
Each CLI subprocess now imports directly from its **verified, immutable source
checkout** while the venv supplies dependencies. The workflow confirms the
CLI schema is available and the imported `devtool.__file__` belongs to the
pinned checkout before any plan/preflight/invoke action. This is a source-only
workaround for a distinct **OPEN** Devtool wheel packaging bug; it does not
claim installed-wheel distribution qualification.

After local A05-R1 acceptance and a branch push, create a **new**
`native-only` workflow dispatch (do not replay attempt 1 of run 39296491876).
Pass the NEW run ID and the NEW branch HEAD to the existing exact-run verifier.

## A05-R2: qualify existing successful run without redispatch

GitHub [run 39301086093](https://github.com/Mikeyphw/Cinderbox-Companion/actions/runs/39301086093)
completed successfully at commit `7675f3471326b3ca52a9474a17d96a6bde2943d6`
with attempt `1`. The native DAG succeeded and the Android build was skipped
as required for `native-only`. Artifact ID `12211842809` includes the complete
successful plan, preflight and invoke evidence. The first verifier falsely
refused because the GitHub workflow-run REST response lacked `inputs`, and it
would then have falsely rejected the successful `--machine-file` invoke JSON
for lacking `result.success`.

A05-R2 repairs *only* the read-only verifier. If GitHub inputs are missing,
prove the dispatch scope using the source-bound job guards committed at the
**selected remote run's exact SHA**, and the exact job conclusions. Present
conflicting inputs still refuse. The EXO invoke receipt must have success,
exit zero, operation status `ok` and zero failure/error counters. The complete
artifact SHA256 manifest must match. No source-only qualification implies
an Android device, signed distribution or release qualification.

After installing A05-R2, use the existing successful run ID:

```sh
python3 scripts/devtool/a05_actions_qualification.py verify-run \
  --run-id 39301086093 \
  --sha 7675f3471326b3ca52a9474a17d96a6bde2943d6 \
  --mode native-only \
  --out "$HOME/cinderbox-a05-39301086093"
```

Do not repeat or replay that GitHub dispatch. The output folder must be empty
or absent; the verification command downloads the exact artifact read-only.
