# M2 — trust-boundary hardening (phase A)

Changes are source-level gates, not proof that an APK or third-party archive is safe.

- Companion app update releases are read from `Mikeyphw/Cinderbox-Companion`, not upstream.
- Updates must carry a GitHub release-asset `digest` field in `sha256:<64 hex>` form.
- APK source URL, redirect endpoint, filename, declared size, SHA-256, and Android package ID are checked before the installer receives a file.
- Absence of a digest is a **hard failure**, not a reason to accept an unsigned asset.
- A successful GitHub Actions **debug** build is not automatically a release. No release signing or automatic publication is configured.
- Mod ZIPs are bounded by entry count, per-file size and total uncompressed size, and restricted to the selected extraction directory.
- Save bundles have entry/size limits and reject duplicate names during import.

## Remaining M2 work

- Third-party Cinderbox and SMAPI downloads need their own source/digest policy (not automatically pinned to this fork).
- SMAPI extraction has two paths and requires a transactional stage/rollback rather than merely per-entry checks.
- Device install smoke and signature-update continuity must be verified using **the fork's own signing identity**, never the upstream developer's APK.
- Mod installation replacing an existing mod requires a manual backup/rollback test on-device.

## Test gates

`./devtoolw security` checks source invariants from M0/M1 only; the newly added JUnit tests are picked up by
`./devtoolw quick` and the hosted `:app:testDebugUnitTest` job. Lint and debug APK checks run in the
hosted Devtool Actions workflow. No production release certification is claimed.
