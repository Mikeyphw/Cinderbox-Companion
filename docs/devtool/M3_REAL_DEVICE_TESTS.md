# M3 Android real-device test plan (interactive, not automatic)

Use a test-only Steam account or temporary save fixture; always make independent backups. Root and Shizuku should be tested *separately*, only after explicitly enabling the corresponding access method in Settings. Don't test with your sole Stardew save.

1. **CI/source:** Push to `security/m0-m1-hardening` over SSH, confirm the GitHub Actions debug pipeline passes, and dispatch `devtool actions android run` with `--project-dir . --module app --variant debug --format apk --ref security/m0-m1-hardening --yes` (your existing workflow). Collect with `devtool actions android collect` using the actual run/artifact IDs and `--expected-package com.sdvsync`.
2. **Device preflight:** Connect exactly one device to ADB. `python3 scripts/devtool/m3_device_probe.py --output .devtool/reports/m3-device-preflight.json`. This only records SDK, Android release, ABI and source SHA. It **does not** assert installation or passing tests.
3. **Instrumentation:** Run `./devtoolw device` with a configured Android SDK/device backend. Devtool executes `:app:connectedDebugAndroidTest`. Review real test counts, logs and failure messages; never count a missing SDK, emulator, or ADB connection as a pass. Instrumentation installs test binaries and runs tests on the device, so opt in deliberately.
4. **Manual M0/M1:** In Settings, verify root is **not** automatically requested; SAF remains available on rooted phones. Check Shizuku with and without an active service; opt in to root only for approved save paths. Verify permission denial degrades safely.
5. **Manual M2:** In a disposable Stardew folder, try mod installation/update/cancellation, ZIP traversal/oversize refusal, SMAPI download integrity check, interrupted SMAPI replacement/recovery, and restoration of the previous install. Compare a backup before and after.
6. **Sync/regression:** With a test fixture, exercise save list, export/import/backup, one Steam Cloud download and upload after confirming conflicts, mod enable/disable and UI reopen after process death.
7. **Device matrix:** Repeat on at least one Android 13 and one Android 14+ device or emulator, including a rooted and non-rooted configuration where available. Capture separate evidence. Record exact Devtool run IDs, expected vs observed behavior, failures and recovery.

Debug CI outputs use ephemeral debug certificates, so one CI APK may not upgrade another. Uninstalling for debug-signing mismatches **can erase local app data**; back up app state and game saves first. Do not work around a mismatch by force-installing over an unknown existing package.

Evidence checklist: source SHA; Devtool run ID; test command; APK SHA-256 and public signing certificate; device SDK/ABI; root/Shizuku mode; test count and assertions; test backup identifier; log location; actual failures; rollback result. The preflight JSON alone never qualifies a release.
