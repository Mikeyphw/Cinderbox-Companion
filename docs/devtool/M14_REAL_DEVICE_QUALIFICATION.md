# M14 — Isolated Android real-device qualification

Purpose: verify real Android execution without destructive operations on the user's saves,
mods, Steam credentials, or installed game files.

The device runner requires a successful repository-identical GitHub Actions build, exact source
commit, successful M3–M13/M14 CI steps, downloaded `debug-apk` and `m14-androidtest-apk`
from the **same run**, M3/M13 evidence consistent with the APK bytes, and an explicit
`--install` flag. It refuses existing app/test package replacements unless `--allow-replace`
is supplied. Android's own signature check still applies; no uninstall or data clearing.

## Execute from Termux after successful feature-branch CI

```sh
cd "$HOME/Code/Cinderbox-Companion"
RUN_ID="$(gh run list --repo Mikeyphw/Cinderbox-Companion \
  --branch feature/m14-isolated-device-qualification --workflow build.yml \
  --limit 1 --json databaseId --jq '.[0].databaseId')"
python3 scripts/devtool/m14_device_qualification.py \
  --run-id "$RUN_ID" --transport termux-root --install \
  --output "$HOME/Downloads/cinderbox-m14-device.json"
```

If an app copy is installed already, investigate its origin and signing identity before
*explicitly* choosing `--allow-replace`. A CI debug key may not match an installed debug or
release app; Android will reject the upgrade. Never use uninstall/clear as an automatic fallback.

For a separate host with one authorized `adb` device, use `--transport adb`.
With `--launch`, the runner only proves activity-start acceptance, not interactive UI success.

## Scope and interpretation

Eight instrumentation cases verify isolated temporary-data workflows: checkpoint ownership,
profile rollback after simulated interruption, two-mod rollback on injected failure,
independent journal corruption, safe save restoration, save corruption fail-closed,
Operation Center concurrent errors, and size-unknown planning. No actual Steam login,
user's save trees or Mods directories are accessed by the tests.

The JSON statuses are: `ci`, `install`, `instrumentation`, optional `launch`, and `overall`.
No device serial, hardware ID, file path, raw shell output, or personal data is included.
A failed or blocked run still produces `FAILED_OR_BLOCKED` JSON with a closed-vocabulary
`failure_code`. A green run is **not** production qualification. `device_qualified` stays false;
`publication_allowed` remains false. Reproducible builds, stable release key, full UI and
real interruption/reboot tests require separate explicit work.
