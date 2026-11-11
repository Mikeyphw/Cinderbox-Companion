# CB-NX06 LAB03B — Physical Android 16 + isolated Firefox LAB witness

**Only LAB03A hosted API36 is complete.** LAB03B adds bounded, read-only physical evidence collection and **does not** install an APK/XPI, launch pairing, authenticate Nexus, download mods, inspect production saves/Mods, delete files, grant permissions, or claim physical acceptance without an authorized session.

## Source and identity boundaries

- Android LAB is the **full Compose app** `com.sdvsync.cbnx06lab`, private `filesDir/CBNX06_GAME_LAB` and localhost `38472`; production stays `com.sdvsync`, external Stardew data, and `38471`.
- Browser LAB Gecko ID: `stardew-nexus-download-queue-cbnx06lab@mikeyphw.scriptexts`. Production Gecko ID remains different.
- The CI LAB XPI is **unsigned**. A hosted build is **not** evidence that Firefox or Iceraven will accept/install it. Never bypass browser signature requirements, never silently replace an extension. Manual installation requires a supported browser mechanism and user approval.
- The LAB manifest omits production NXM handlers. Never tap direct NXM manager actions pointing to production Cinderbox during LAB testing.
- Keep the existing Firefox production extension and manual downloads / other-manager UX untouched.

## Run and evidence sequence (Termux/Zsh safe)

The self-launching `CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip` embeds a Python/Rich launcher. No worktrees or permanent-checkout edits. The launcher validates Android PR #89 and browser PR #2, source/blob pins, CI, then performs a non-force push to the existing Android PR branch. No local Gradle build.

```sh
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip --offline-test
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip --yes
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip --resume-only
```

When the **new LAB03B workflow and full LAB APK workflow both pass** on the exact new Android source SHA, download the corresponding hosted Android LAB APK and browser XPI with verified attestations. The launcher selects successful exact-source workflow runs; all artifacts are written to a new, private **local** directory. The browser XPI remains unsigned.

```sh
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip artifacts \
  --output-dir "$HOME/.local/share/cbnx06-lab03b/artifacts-01"
```

Run the **read-only physical preflight**. This verifies Android API 36 + arm64, refuses emulator identifiers, reads installed package identities and hashes; it does not install the LAB APK and does not inspect production game contents.

```sh
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip device preflight --serial localhost:5555
```

If `com.sdvsync.cbnx06lab` is not installed with **exactly the attested hosted bytes**, the capture refuses. The user must authorize a separate LAB-only installation, after inspecting its signer and installed package. **This launcher will never install/uninstall any app.**

For a consented test, choose a **synthetic or otherwise harmless exact fixture** mod+file ID and substitute the two numeric IDs. Never expose Nexus credentials, pairing codes, NXM URLs, cookies, or tokens in shared output.

```sh
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip device before \
  --serial localhost:5555 --mod-id 12345 --file-id 67890 \
  --artifacts "$HOME/.local/share/cbnx06-lab03b/artifacts-01" \
  --session-dir "$HOME/.local/share/cbnx06-lab03b/session-01"
```

**Manual, approved browser actions only:** install/enable the independent LAB Firefox/Iceraven extension *only using a legitimately supported route*, open the full LAB Android app (not production), enable pairing, pair the nine-digit code to localhost port **38472**, opt into exact-file inbox handoff, submit the selected ID pair, observe the pending private inbox entry and revoke pairing. The inbox cannot start a native download or install anything. Avoid the production NXM handler. Record privately whether the browser actually installed and paired; do **not** claim installation solely from a local XPI file.

```sh
python3 /storage/emulated/0/Download/CBNX06_LAB03B_READ_ONLY_CONSOLIDATED.overlay.zip device after \
  --serial localhost:5555 --mod-id 12345 --file-id 67890 \
  --session-dir "$HOME/.local/share/cbnx06-lab03b/session-01"
```

This only observes a fresh, exact mod/file entry in the app-private LAB inbox (if `run-as` permits read-only access), and confirms production and LAB installed APK identities remain unchanged. It exports no raw inbox, request IDs, passwords, or private paths. **A new entry does not independently prove its browser origin.** Source-signed XPI installation, user consent, negative Host/Origin/port cases, revocation, restart and offline fallback still need manual confirmation and separate evidence.

## Qualification ceiling

Even with all hosted tests green and a physical `READ_ONLY_EXACT_INBOX_OBSERVED_NOT_FULLY_QUALIFIED` receipt, `browser_extension_installed_proven=false`, `live_browser_pairing_proven=false`, `nexus_file_provenance_verified=false`, `production_game_unchanged_proven=false`, and `release_qualified=false`. Physical installed APK byte equality and production **APK hash** stability are not evidence that game-file contents were unchanged. A separate authorized bounded game data inspection and live browser acceptance are future gates.

## Roadmap

LAB03B read-only and live manual pairing → LAB03C user-driven exact-file action → LAB03D private archive/hash evidence → LAB04 synthetic LAB-only install/rollback → LAB05 E2E UI → LAB06 physical acceptance/rollback → CB-NX07 final parity/release decision. No auto-merge, publishing or release signatures.
