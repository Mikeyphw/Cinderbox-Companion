# M18 — Real process termination and recovery (debug only)

This milestone is not Activity recreation, a synthetic lifecycle callback, or a reboot.
M18 runs two **M18-only** AndroidJUnitRunner methods separated by a genuine
`am force-stop com.sdvsync` and an independently verified Activity cold launch.
It checks that an isolated randomly named private SharedPreferences test marker
survives and removes that marker after successful recovery verification.

## Safeguards

- **Opt-in only**: `--force-stop-opt-in --ui-opt-in --test-profile-opt-in --install --allow-replace`.
- Use an **intentionally signed-out test installation** with **no active downloads,
  operations, foreground sync, or other jobs**. A force-stop interrupts the process,
  services, alarms, and background work; this can affect ongoing operations.
- No `pm clear`, uninstall, reboot, root escalation unless `--transport termux-root`
  was expressly selected, permission grants, external storage access, or Steam login.
- The process gate verifies a running process before stop, no process after stop,
  and a running process after cold relaunch. It does **not** claim power-loss,
  kernel-crash, reboot, service rescheduling, or full save/mod recovery.
- A marker can remain on an interrupted/failed run. It has no personal content,
  is located in the isolated `cinderbox_m18_test_only` prefs file, and the host
  report deliberately does **not** include its random key or any app data.
- APK and instrument APK downloads are bound to the GitHub PR merge checkout
  and verified through existing M3/M13/M14 provenance.
- Does not rerun M14, M15, or M17 cases. Release and publication stay BLOCKED.

## Use after PR CI succeeds

```bash
python3 scripts/devtool/m18_device_qualification.py \
  --run-id <M18_PR_CI_RUN_ID> --transport termux-root \
  --ui-opt-in --force-stop-opt-in --test-profile-opt-in \
  --install --allow-replace --output "$HOME/cinderbox-m18-device.json"
```

Run with screen unlocked, with Cinderbox's test account signed out, and no jobs
running. Do not merge before the M18 source-bound device report passes.
