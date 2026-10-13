# M2B — GitHub release integrity and crash-safe SMAPI installation

Source gate: `security/m0-m1-hardening` at `7c41accc1abdd26f6a189c89e6b5dc7a7ee38e2d`.

## Trust policy

- Cinderbox APK is accepted only from `Ekyso/Cinderbox` GitHub releases and must identify as `com.game.cinderbox`.
- SMAPI is accepted only from `Ekyso/SMAPI-for-Cinderbox` release assets.
- Both releases **require** a GitHub asset `sha256:` digest, an allowed HTTPS GitHub download/redirect, and an exact byte count. Cache writes stage then rename atomically.
- The SHA-256 in GitHub's API is a transport integrity check, **not** independent publisher-signature verification. GitHub repo compromise still matters. Android OS enforces signature continuity on updates to installed packages; no in-app signer pinning is provided in M2B.
- Old cached SMAPI files are re-hashed against the latest release metadata before installation.

## Transaction policy

- Unzip into a sibling staging directory on the same filesystem, with per-entry and total extracted-byte limits, entry count limit, path validation, and duplicate detection.
- Rename the old directory into a sibling backup, then promote the staging directory; on failure restore the backup.
- On next operation, recovery recognizes an old-backup-without-target state and restores it. When a completed promoted tree has transaction markers, cleanup is resumed. If state is ambiguous, stop without deleting the old copy.
- The routine **replaces** the SMAPI internals directory, preserving the previous version only for the transaction window; it does not merge arbitrary files from the old SMAPI directory. Back up user customizations before upgrading.
- `copyToCinderbox()` invokes the same verified, transactional installer and never falls back to direct ZIP extraction.

## Qualification

Run `./devtoolw security`, `./devtoolw quick`, and the native Devtool GitHub Actions Android debug build. The source-level security contract alone does not validate these new behaviors. The JUnit `SmapiTransactionalInstallerTest` contains positive and negative tests. Real-device validation must separately cover unplugging/restarting during install and low-storage failure (after backing up game data). No production signing secrets are required.
