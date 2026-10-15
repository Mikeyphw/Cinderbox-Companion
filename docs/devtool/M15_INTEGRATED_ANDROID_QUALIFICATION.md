# M15 — Cross-feature Android qualification (first automation slice)

M14 concluded **8/8 PASS** against source `82d5be7431383d861c5a1d51d9308ea71aa2b5ff`,
Actions run `38810574418`. This evidence is historical and MUST NOT be
reinterpreted as M15 or a production release pass.

M15 exercises six cross-feature scenarios using a new `M15IntegratedDeviceTest`
class. Fixtures are created under a canonical, uniquely named
`targetContext.cacheDir/m15-device-*` and guarded by a `.m15-owned` marker.
The scenarios combine live production logic from `GameDownloadRecovery`,
`ModBatchTransaction`, `SaveRestoreTransaction`, `InstallationScanner`,
`StoragePlanner`, and `OperationCenterPolicy`. Android instrumentation invokes
**only M15 tests**, not M14's already-passed tests.

1. Interrupted two-mod install rolls back without losing a pending game download or an unrelated save.
2. Save restore preserves custom files and leaves a separate download checkpoint valid.
3. A corrupt save journal blocks restoration, preserves the live save, and does not poison the download checkpoint.
4. Incomplete game files and an unknown download size cannot become a positive installation/storage decision.
5. Multiple recovery indicators result in read-only, de-identified guidance without changing a fixture.
6. A symlinked installation is rejected without rewriting its target.

## Local source checks (no root, network or device)

```sh
./devtoolw m15-check
python3 -m unittest discover -s scripts/devtool -p 'test_m14_*.py' -v
```

`build.yml` runs M15 offline regressions before the *existing* Gradle test,
lint, debug APK, and Android-test APK build steps; it uploads the existing
`debug-apk` and `m14-androidtest-apk` artifacts. There is no second Android
instrumentation APK build or duplicate M14 device test.

## Explicit M15 on-device command (Termux root)

Use the green **M15 branch CI run** from the exact pushed commit, not M14's old
run. In Termux at that exact commit:

```sh
cd "$HOME/Code/Cinderbox-Companion"
python3 scripts/devtool/m15_device_qualification.py \
  --run-id YOUR_GREEN_M15_CI_RUN_ID \
  --transport termux-root --install --allow-replace \
  --output "$HOME/Downloads/cinderbox-m15-device.json"
```

The runner checks M3/M13 evidence, repository/branch/commit, synthetic PR
merge parentage, CI steps, and APK SHA-256 before requesting any install. The
`--install` consent is required; `--allow-replace` is a *separate* opt-in to
updating the two existing APK packages. It does NOT bypass Android signing
checks. A fresh GitHub-hosted runner may rotate its debug signing certificate:
if Android rejects the update, **stop** and inspect signing identities. The
runner never uninstalls packages, clears data, retries with dangerous flags,
or grants device privileges implicitly. User-owned data cannot be assumed
safe from an explicitly chosen manual uninstall.

## Scope boundaries

This first slice does **not** claim interactive UI navigation, Steam login,
actual permissions UI, real killed-process/reboot recovery, or work on user
save/mod/game directories. `launch` is NOT_RUN. Those are separate M15
acceptance tasks that need a hermetic UI fixture and explicit review.

M15 evidence always has `device_qualified=false`, `release_qualified=false`,
`publication_allowed=false`, `automatic_device_install=false`. A successful
result `PASS_ISOLATED_INTEGRATION_AUTOMATION` means only that these six cases
executed and passed on a real device using the verified debug APK.
