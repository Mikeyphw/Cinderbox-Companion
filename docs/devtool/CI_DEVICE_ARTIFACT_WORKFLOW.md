# Cinderbox Companion — reusable CI APK/device qualification

**Status:** implemented in an additive native Devtool overlay; actual on-device execution requires a chosen CI run and explicitly selected tests.

## Usage

From a matching source checkout:

```bash
python3 scripts/devtool/ci_artifacts_device.py --list-tests
python3 scripts/devtool/ci_artifacts_device.py \
  --run-id 39136540831 --serial emulator-5554 --test m24-staged --test m24
```

For the new M24 PICS lane after its source is applied and built in CI:

```bash
python3 scripts/devtool/ci_artifacts_device.py \
  --run-id YOUR_SUCCESSFUL_RUN_ID --serial emulator-5554 --test m24-pics
```

Use `--test m24-staged,m24-pics` for multiple lanes, `--skip-install` for exact-byte checking without reinstalling, `--app-artifact` and `--test-artifact` for other artifact names, and `--output-root` to choose receipt storage. Omitting `--test` installs/attests the pair but does not run tests. A lane is discovered from an existing `scripts/devtool/<lane>_device_run.py` file: no hardcoded run IDs or milestone lists.

## Safety and qualification boundaries

- Refuses non-successful/mismatched-repository GitHub workflow runs.
- Requires explicitly selected ADB serial; does not interpret multiple ADB transports as multiple physical devices.
- Downloads an unambiguous app and test APK, then installs with `adb install -r -t` without uninstall or data clear; certificate-mismatch failures stop.
- Validates installed APK SHA-256 against the downloaded CI bytes, and fails closed for split/unreadable APK paths.
- Normally requires local `git HEAD` to equal the CI source SHA before invoking local test scripts; `--allow-source-mismatch` is explicit and not recommended.
- Runs only requested app-private instrumentation lanes; each lane's receipt must confirm all cases PASS.
- Retains downloaded APKs, individual JSON receipts and a consolidated `summary.json` for each invocation.
- Does not test real Steam entitlement, authenticated depot file manifests, or release qualification; does not modify main Cinderbox game files or saves.

## Devtool improvement observation

**Evidence:** M23 and M24 required repeated one-off scripts for retrieving `debug-apk` and `m14-androidtest-apk`, installing them, and invoking selected synthetic Android runners. One-off scripts were pinned to particular run IDs and test suites, creating avoidable repetition and stale-harness risk.

**Affected:** Cinderbox Companion's Devtool Android qualification, Termux/ADB workflow; applicable pattern to other Android targets.

**Resolution:** additive standalone Python CLI, dynamic lane discovery, explicit test selection, exact CI metadata verification, installed byte-hash attestation and persistent receipts. No changes to Devtool core or repository-wide workflow definitions.

**Remaining:** migrate this observation into the cumulative `docs/devtool/DEVTOOL_IMPROVEMENTS.md` during the next consolidated update. The current add-only overlay intentionally does not edit that ledger so it can be applied before or after the in-flight M24 PICS overlay without conflicting source preimages.
