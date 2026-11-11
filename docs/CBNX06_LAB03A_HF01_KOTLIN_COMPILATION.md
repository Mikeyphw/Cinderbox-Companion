# CB-NX06 LAB03A HF01 — AndroidTest compilation recovery

Source pin: `7b7bdcbb9641b3746355746ac8c28387bc766b6d`, PR #89. This is a source/CI hotfix, not physical Nexus acceptance.

## Confirmed errors in hosted runs

- `CbNxLab03DeviceTest.kt:69-70`: an accidental archive durability check referred to `archiveFile`, `expected`, `sha256`, and `digest`, all undefined in this test. Removed these two test-only lines. The actual `NexusLab03Evidence.previewSynthetic()` still checks the archive bytes and receipt hash before returning, unchanged.
- `:app:compileCbnxLabAndroidTestKotlin`: inherited `M20ConsolidatedDeviceTest` references `M20SyntheticWorkerService`, which belongs to `src/debug/java`; the custom lab build type did not compile that source folder. `cbnxLab` now adds precisely that **source** directory without adding the debug manifest, production package permissions or service declarations. Existing production debug/release configuration is unchanged.

## Preserved guarantees

- Standalone synthetic preview remains LAB-only with app-private ZIP and receipt, canonical mods root, no installation or live Nexus claims.
- PR #89 stays open, no forced push/merge/rebase, no physical device operations. PR #2 is unchanged.
- All existing tests remain present; LAB03A still builds the isolated instrumented APK and runs its two target tests against API36 after hosted compilation.
- The source gate and mutation suite now refuse recurrence of unbound test identifiers and loss of the lab-only debug synthetic worker source.

Qualification is pending hosted CI and API36 emulator execution; successful source tests alone are not sufficient.
