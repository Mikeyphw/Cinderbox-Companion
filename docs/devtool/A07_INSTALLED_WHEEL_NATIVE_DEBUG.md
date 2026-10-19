# ACTIONS-A07 — installed-wheel native debug APK build

A07 is an opt-in boolean job in the already registered `.github/workflows/devtool-android-build.yml` `workflow_dispatch` workflow. The new job is inserted **before the unchanged A05 job** to preserve its existing source contract. The previous legacy Android build and A05 DAG remain available, with no automatic device installation, release signing or publication. GitHub only dispatches newly added workflows once present on the default branch, so this approach avoids depending on a not-yet-registered standalone workflow.

Devtool is pinned to the accepted A06 producer `409c5527532eaa1ee62b8111e030732d3f9e2791`. The Ubuntu runner installs Devtool into a venv from that exact Git commit. It proves that `site-packages/devtool/core_cli_schema.json` exists and the canonical CLI import is from the installed wheel. No `PYTHONPATH` source checkout workaround is used.

The existing target-local Cinderbox native workflow `build` runs `security-contract → debug-apk → verify-debug-apk` through Devtool plan/preflight/invoke. M16 provisions the preexisting pinned CI debug signer, verifies the assembled APK certificate, and refuses missing credentials. The established M3 producer generates self-reported build/APK SHA-256 evidence; M13 independently checks that evidence and records the explicit device/release boundary. Exactly one APK is staged.

Two artifacts: `cinderbox-a07-machine-evidence` (uploaded even on failure, marked incomplete) and `cinderbox-a07-debug-apk` (uploaded only following all host checks). Evidence records the exact repository, source SHA, Devtool SHA, GitHub run ID/attempt, all machine receipts, signer/report consistency and digest. No token, keystore, password, or signing private key is included in artifacts.

Local source qualification:

```sh
python3 scripts/devtool/a07_native_debug.py source
python3 -m unittest discover -s scripts/devtool -p 'test_a07_native_debug.py' -v
python3 scripts/devtool/m3_build_evidence.py source
python3 scripts/devtool/a07_acceptance.py --repo "$PWD"
```

Dispatch manually after pushing the accepted A07 commit:

```sh
gh workflow run devtool-android-build.yml --repo Mikeyphw/Cinderbox-Companion \
  --ref feature/m24-steam-download-safety \
  -f project_dir=. -f module=app -f variant=debug -f format=apk \
  -f a05_mode=native-only -f a07_native_build=true
```

Inspect the exact resulting run and its SHA. Do not qualify an unrelated latest run. After run succeeds, verify run ID, attempt and **exact consumer commit**:

```sh
python3 scripts/devtool/a07_native_debug.py verify-run \
  --run-id RUN_ID --attempt 1 --sha FULL_CINDERBOX_SHA
```

`verify-run` checks GitHub REST run/job/step outcomes, exact artifact identities/digests and the downloaded contents with local source/run, native machine, APK, M3 and M13 consistency. GitHub artifact digests attest archived bytes, not release qualification. Keep device and production release qualification separate.

Safety rules: don't accept a wheel source import, a modified Debug signer, missing or duplicate APKs, a non-successful DAG node, incomplete machine JSON, unverifiable GitHub run, or any claim of release or device qualification. Failure is non-qualification, not an instruction to install or publish anything.

A07 explicitly requires `a05_mode=native-only` so the established heavy legacy build is skipped. The A05 read-only job also runs; the A07 remote verifier requires that A05 succeed, the legacy job be skipped, and the A07 host build succeed. Existing A05 historical evidence is not modified.

## A07-R1 runner context repair

GitHub rejected the first A07 dispatch (HTTP 422, workflow line 422): `runner.temp` is unavailable in job-level `env`. A07-R1 scopes `DEVTOOL_XDG_DIR` to the two Devtool-consuming steps, adds parser-context regressions, and preserves A05 and the original A07 provenance. The original A07 local acceptance is tied to its historical commit; A07-R1 validation is performed by the corrective overlay.
