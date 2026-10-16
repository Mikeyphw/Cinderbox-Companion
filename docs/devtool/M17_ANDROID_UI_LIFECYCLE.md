# M17 — explicit Android UI navigation and Activity lifecycle (first slice)

M14 (8/8) and M15 (6/6) are historical, immutable qualifications. M17 is a
**separate** real-device UI lane; its own `M17OfflineUiDeviceTest` class runs
four tests on the production `MainActivity` and actual Compose screens:

1. Signed-out Settings reached without Steam credentials.
2. Settings → Operation Center: read-only warning is visible.
3. Real Android `ActivityScenario.recreate()` preserves offline Settings navigation.
4. Operation Center refresh and Back return to Settings without starting recovery.

## Safety and boundaries

**Use a dedicated, intentionally signed-out Android test profile.** MainActivity
is real: it may resume an existing Steam session, start the configured background
service, or query normal app state. The instrumentation **does not** clear app
credentials, revoke permissions, uninstall packages, log out, or mutate saves,
mods, downloads, backups, or Steam directories. A signed-in profile must NOT be
silently converted to a test profile. UI assertions fail if "Continue offline" is
not available. Tests do not press buttons for downloads, restores, permission
prompts, document export or destructive operations. Running against a real app
profile may still expose existing in-app state, so opt in only on a test profile.

Activity recreation is NOT a killed process, force-stop, device reboot, or a
persistent-journal replay qualification. Those require separate carefully
designed M17 follow-up tests. This slice does not prove production release,
publication, real permission-denial recovery, or that live Steam integration is
safe under process death.

## Devtool host validation

```sh
./devtoolw m17-check
python3 -m unittest discover -s scripts/devtool -p 'test_m17_*.py' -v
```

Both regular CI and the Devtool Android workflow compile the Android test APK
via their **existing single** `:app:assembleDebugAndroidTest` step. The pinned
M16 debug certificate gate must pass for both APKs; M14 and M15 instrumentation
are not re-executed. The runner binds the actual run/PR checkout and M3/M13 APK
SHA-256 evidence through the M14 verifier and writes sanitized per-case JSON.

## Explicit Android execution after M17 CI is green

On the exact pushed M17 commit and on a **signed-out test installation**:

```sh
python3 scripts/devtool/m17_device_qualification.py \
  --run-id YOUR_GREEN_M17_CI_RUN_ID \
  --transport termux-root --ui-opt-in --install --allow-replace \
  --output "$HOME/cinderbox-m17-device.json"
```

`--ui-opt-in` is mandatory even with `--install`. `--allow-replace` is a separate
opt-in, never a signature bypass. **Do not uninstall just to pass M17**; pinned
M16 signing exists to permit a data-preserving update once key identity matches.
The runner never automatically uninstalls or clears data, never prints raw
instrumentation output into its JSON, and never re-runs M14/M15 device tests.

An M17 PASS means four test methods executed with a successful AndroidJUnitRunner
final code; it keeps `device_qualified`, `release_qualified`, and
`publication_allowed` false by design.
