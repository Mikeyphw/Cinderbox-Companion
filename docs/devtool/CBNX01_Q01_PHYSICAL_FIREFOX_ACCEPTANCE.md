# CB-NX01 Q01 — real Iceraven/Firefox Android -> Cinderbox staging observation

**Status:** Read-only qualification harness, **NOT a real-device pass certificate**.

This is the next gate after the independent Cinderbox PR #85 and scriptexts PR #1 hosted CI checks. Do not start CB-NX02 native queue work or enable release flags merely because hosted tests are green.

## Preconditions

- Real **Android 16/API 36, ARM64** phone accessible via ADB `localhost:5555` from Termux. The script refuses Android emulators, unrelated adb serials, and non-debug Cinderbox installations.
- Debug Cinderbox APK installed from the current Cinderbox CI run; compare its SHA-256 to the source-bound CI APK to establish test artifact provenance.
- **Iceraven** (`io.github.forkmaintainers.iceraven`; tested target: 2.52.0) or a supported Firefox for Android distribution, with Stardew Nexus Download Queue actually installed and enabled. An installed browser package does **not** verify that the extension is enabled or compatible.
- User is signed into Nexus in the chosen Iceraven/Firefox browser with an authorized account. No credentials or cookies are collected by this test.
- Cinderbox Mods directory is accessible at `/storage/emulated/0/StardewValley/desktop/Mods`. No existing pending mod review (complete or discard one manually in-app first).
- Pick a legitimate, downloadable **Stardew Valley mod ID and specific file ID**. Do not reuse a browser URL if its Nexus authorization expired.

Iceraven is a Gecko browser, but add-on installation and external-app prompts must still be verified on the phone. The app launcher explicitly targets Iceraven first; a normal HTTPS browser fallback is not proof of a successful extension handoff.

## Read-only before witness

From the Cinderbox checkout on the Q01 feature branch:

```zsh
python3 -B scripts/devtool/cbnx01_physical_acceptance.py before \
  --serial localhost:5555 \
  --mod-id YOUR_MOD_ID --file-id YOUR_FILE_ID \
  --expected-apk-sha256 YOUR_CI_APK_SHA256 \
  --evidence-dir "$HOME/Code/CBNX01_Q01_EVIDENCE"
```

The script stores **only** sanitized local state: Android API and device class, installed app SHA-256, compatible Gecko browser package availability, private Cinderbox pending-review ZIP SHA-256 if present, and a hash of the Mods directory **listing** (not of contents). It neither installs apps nor sends NXM links. `run-as` needs a debuggable Cinderbox build.

## Actual user action

Open the selected Cinderbox mod file, choose **Browser + NXM**, use Iceraven or Firefox, and complete Nexus login/requirements/waiting and any Android external-app confirmation **manually**. Confirm that the selected mod and file remain the same. If the page cannot open the selected file or Iceraven/Firefox cannot invoke Cinderbox, record that as **blocked**. Do not invoke a fabricated `nxm://` URL or click on another file to force success. **Do not approve/install the staged mod** yet.

## Read-only after witness

```zsh
python3 -B scripts/devtool/cbnx01_physical_acceptance.py after \
  --serial localhost:5555 \
  --evidence-dir "$HOME/Code/CBNX01_Q01_EVIDENCE"
```

The result `STAGING_OBSERVED_NOT_FULLY_QUALIFIED` proves only that the physical Cinderbox debug build has a new pending archive with source `nexus`, the expected **mod ID**, and an unchanged Mods *directory listing*. It **cannot** independently prove the Nexus **file ID**, that the Iceraven/Firefox extension was enabled, that an Android prompt was accepted, that downloaded bytes match Nexus provenance, or that Mods file contents were unchanged. Those are still open acceptance items requiring additional instrumentation/independent evidence.

If the result is `INCONCLUSIVE`, read only the allowlisted `failure_codes` in `after.json`; do not share raw Nexus links, browser cookies, tokens, raw logcat, private mod lists, or `.properties` contents. The receipt **never** asserts `release_qualified=true`.

## Next milestone

CB-NX01 Q02 should bind file ID to the staged archive's local metadata and provide independent, source-bound receipt of the selected file and Android handoff result. CB-NX02 persistent queue begins **after** CB-NX01 live acceptance, not in place of it.
