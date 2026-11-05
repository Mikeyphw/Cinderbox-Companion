# R48A R4 — real Operation Center action-label hotfix

## Evidence and exact failure

- PR: https://github.com/Mikeyphw/Cinderbox-Companion/pull/54
- Hosted workflow: https://github.com/Mikeyphw/Cinderbox-Companion/actions/runs/41902096586
- Verified branch head before overlay: `6b690874289aa86163ccd69806152493df830ec0`
- The Android API36 emulator booted, debug APK built, R40 source tests passed, and 3/4 real MainActivity instrumentation tests passed.
- The only failing test was `realOperationCenterReadOnlyReturn`, privacy-safe checkpoint `open_center`.
- `HomeScreen.kt` renders a button with text `Open operation center` and callback `onOpenOperationCenter`.
- The instrumentation test incorrectly searched for `View operation center`, which does not exist in the actual Home UI.

## Change

1. Update the Compose test's selector to `Open operation center` without changing click behavior or the remaining assertions.
2. Add a host-only unittest pinning the button action label in HomeScreen and the test selector together, blocking future drift.

## Safety and acceptance boundaries

Only test files are modified; no production application logic, Gradle configuration, release policy, device access, Steam credentials, game files, or signing configuration is changed. Existing `r48_gate.py`, R43C checks, and the fail-closed evidence verifier remain intact.

**Pending:** Rerun the real-activity workflow on GitHub. Passing host-only validation does not mean emulator tests or device acceptance have passed. Keep PR #54 open until the hosted workflow passes all four tests and five screenshot-verification gates. No physical-device, TalkBack, Steam, release, or publication qualification is implied.
