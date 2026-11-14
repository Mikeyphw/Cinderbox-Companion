# CB-NX06 — Physical Android 16 and Firefox/Iceraven witness

## Qualification levels (never conflate them)

- `HOSTED_SOURCE_PASS`: Python source policies + 23 negative scenarios + exact-SHA debug Android APK built by GitHub Actions. The hosted runner is **not** a physical device and does **not** authenticate to Nexus.
- `PHYSICAL_READ_ONLY_PREFLIGHT_PASS`: physical API 36 ARM64 detected, no emulator markers, compatible Firefox/Iceraven application and Cinderbox debug `run-as` present. Does **not** prove Firefox extension enabled or live Nexus.
- `EXACT_FILE_PRIVATE_STAGING_WITNESSED`: after deliberate user-driven browser action, a *new* exact-file pairing request, matching native Nexus journal job, app-private review receipt (mod + file + job + SHA), matching archive hash, and unchanged pre-review Mods metadata were observed. App archive hash is independent of the receipt field, but **not** a provider-signed hash.
- **Never** automatically set physical end-to-end qualified, live Nexus authorized, safe install/rollback qualified, or release qualified. These require separately reviewed real-world evidence. Emulator-only receipts cannot satisfy them.

## Installation / app safety

This witness does not call `adb install`, `adb uninstall`, `su`, `pm clear`, or mutate any app/game data. **NO auto-install**, no cleanup, no privilege escalation, no browser cookies/tokens or NXM bearer URLs. Do not uninstall the currently installed Cinderbox package just to match a debug signing key. If the signed debug APK cannot be safely installed without losing app data, report the blocker instead of bypassing it. Back up real Mods and game saves before any later **manual** test involving install or rollback.

## Termux / Zsh-safe invocation

The deliverable is a self-contained Python/Rich zipapp. First run its source workflow with
`python3 /storage/emulated/0/Download/CBNX06_PHYSICAL_E2E_CONSOLIDATED.overlay.zip`.
Its `device` subcommand is read-only and usable even before source application.

```sh
python3 /storage/emulated/0/Download/CBNX06_PHYSICAL_E2E_CONSOLIDATED.overlay.zip device preflight --serial localhost:5555 --ack I_AUTHORIZE_READ_ONLY_DEVICE_PROBE
```

Download the *exact* debug APK from the new successful workflow's artifact into a private Termux directory; do not assume that artifact is already installed. Both `--apk-file` and `--apk-attestation` are required. The launcher hashes the local APK without installing it, validates the accompanying `SOURCE_ATTESTATION.json` against the exact current Cinderbox PR commit and the APK bytes, then compares to the installed Android base APK. A raw `--apk-sha256` is optional corroboration but **never substitutes** for the artifact or source attestation. The launcher verifies both PR HEADs before a session, refusing source drift. Do not use a released app with a different signature/bytes.

```sh
python3 /storage/emulated/0/Download/CBNX06_PHYSICAL_E2E_CONSOLIDATED.overlay.zip device before --serial localhost:5555 --ack I_AUTHORIZE_READ_ONLY_DEVICE_PROBE --mod-id 12345 --file-id 67890 --apk-file "$HOME/Downloads/cbnx06-debug/app-debug.apk" --apk-attestation "$HOME/Downloads/cbnx06-debug/SOURCE_ATTESTATION.json" --full-mods-hash --evidence-dir "$HOME/.local/share/cbnx06-acceptance/session-01"
```

Replace example `12345` and `67890` with the actual selected Nexus mod ID and file ID. `--full-mods-hash` computes a separate content fingerprint of files in Mods (read-only; may be slow). Do not run this for massive Mods trees if the cost is unacceptable; without it, byte-for-byte unchanged Mods contents remain *unproven*.

Next, on **real** Iceraven/Firefox Android: install/enable the extension, pair the 9-digit code, enable exact-file handoff locally, select the **specific** Nexus mod file, complete official Nexus authorization, and allow Cinderbox to stage a private archive. Do not approve or install the file yet.

```sh
python3 /storage/emulated/0/Download/CBNX06_PHYSICAL_E2E_CONSOLIDATED.overlay.zip device after --serial localhost:5555 --ack I_AUTHORIZE_READ_ONLY_DEVICE_PROBE --evidence-dir "$HOME/.local/share/cbnx06-acceptance/session-01"
```

Run `device after` multiple times if the authorized download has not yet completed: each creates a new private after receipt; old before evidence is never overwritten. Stop if the source commit, installed APK, browser package set, or Mods contents changed. Evidence files are local (mode `0600`) and contain no raw private journal, NXM URLs, cookies, session tokens or raw filesystem listings. Check the receipt before sharing it externally.

## Manual Firefox/Nexus witness matrix (not automated)

1. Actual Firefox/Iceraven extension enabled in the real device; localhost permissions and pairing are working without desktop native messaging.
2. Login and exact mod/file choice are verified on the official Nexus page. Browser/Nexus did not silently substitute another file.
3. Opt-in Cinderbox destination and explicit native handoff consent are visible; unpaired browser standalone queue and other-manager fallback still work.
4. Pairing revocation invalidates old bearer token; invalid IDs/replayed nonces and cross-origin requests are refused. No secret in exported status.
5. A correct **new** request appears on Android and the independently hashed Nexus private archive reaches review. No download, staged archive or install is claimed from merely receiving NXM or pairing.
6. No automatic install before review; safe ZIP/path/size (1 GiB) checks and destination fingerprint are present. Do not try malicious ZIPs against real personal game data.
7. Pause/cancel/retry/reordering behavior, Android process restart/interruption, and offline fallback are visually verified without duplicate admission or stale URL reuse.
8. Controlled *isolated lab*, not personal Mods: malformed archive rejection, uncertain installation state, rollback integrity and restoration are validated separately. A passing read-only witness is not a rollback proof.
9. User confirms actual physical device, browser version, extension hash, exact commit IDs, app APK SHA-256 and safe redacted evidence. Retain the original manual evidence privately and review it before any release decision.

**Outstanding work even after a read-only witness passes:** independent authenticated Nexus response/file provenance, actual Firefox extension UI evidence, isolated safe-install/rollback negative matrix, manual full release review and signature. No merge, signing, release or publication authorized by this milestone.

## Roadmap continuation

CB-NX06 is a progressive evidence-gathering gate. Once physical read-only and actual browser/manual negative evidence are obtained and independently reconciled, CB-NX07 can address parity polish, accessibility screenshots, packaging/signature and manual release decisions. The original standalone Firefox queue, Vortex/other manager selection, and app-private receipt authority remain unchanged.

## Resume and CI tracking

If a Git push succeeds but the GitHub PR API lags, run the launcher with `--resume-only`. It attests the exact parent, changed-file set, and complete Git blobs before checking the new workflow, and never makes a second commit. `--offline-test` exercises the source policy and negative suite without reading personal device state or touching GitHub.
