# M3D — Local settings without Steam authentication

This patch adds a **Settings** action on the Steam login screen and a separate
`prelogin_settings` outer navigation route. It is not a Steam login bypass.

## Available before Steam login

- Shizuku detection and permission request
- All Files Access and SAF configuration (user-initiated)
- Root access selection with existing confirmation
- Cinderbox mode, local backup retention, and other local settings

Steam logout and root-based cloud auto-sync UI are hidden in pre-login Settings.
The existing authenticated `main` route, save-sync functionality, Steam session
handling, and signed candidate/release workflow are unchanged.

The Settings button is available while Steam is idle, connecting, or in an
error state. Hardware Back or the on-screen Back arrow returns to Steam login.
No login credential, token, or Steam auth state is forged or overridden.

## Validation and scope

The installer first checks the exact Git branch commit and Git blob identities
for all three changed Kotlin sources, requires a clean working tree, verifies
its payload digests, and runs offline regression/contract tests. It rolls back
files on failed installation. This source-bound install cannot replace Android
Gradle compilation or testing on a device.

The `test_m3_prelogin_settings.py` test is copied into `scripts/devtool`, where
it can be executed as:

```sh
python3 -m unittest discover -s scripts/devtool -p 'test_m3_*.py' -v
python3 scripts/devtool/check_security_contract.py
```

Push a feature branch and let GitHub Actions compile and test the APK. Build a
new signed candidate using your existing protected workflow, then install it
on a test device to confirm the Settings button and Shizuku functionality.
Do not overwrite the current signed APK with a different signing key or an
older `versionCode`. To test an actual upgrade, build with incremented version
code after source review; do not uninstall the installed candidate just to
make this UI change.
