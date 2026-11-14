# CB-NX06 LAB06 — Deferred qualification readiness

## Goal

Fold LAB05 HF02 (Compose test-host dependency plus redacted runtime diagnostics)
into the next consolidated source-only milestone. LAB06 creates a strict,
source-bound **readiness manifest**; it does not conduct physical acceptance.

The companion's isolated application ID is `com.sdvsync.cbnx06lab`, and the
isolated Firefox/Iceraven extension ID ends with `cbnx06lab@mikeyphw.scriptexts`.
Only the LAB loopback port `38472` is relevant. The production companion,
NXM scheme, Nexus tokens and Stardew Valley files are outside this milestone.

## Checks

1. The new PR commit must build the isolated Android APK and AndroidTest APK
   under GitHub Actions, with Compose's host activity available to the LAB
   variant (LAB05 HF02 fix). The exact four UI journeys must pass individually.
2. The LAB05 hosted receipt (if later supplied) must match the **exact current
   commit**: four tests, four passes, canonical method names and order, valid
   binary SHA-256 fields, and all emulator-only / no-physical flags.
3. LAB06 emits a bounded redacted `READINESS.json` with the current Cinderbox and
   Firefox PR sources. It marks physical acceptance, real browser pairing,
   Nexus provenance, production file integrity, and release as unqualified.
4. Only after a separately authorized physical workflow may LAB03B read-only
   evidence be gathered; the LAB06 CLI **never invokes ADB or installs APKs**.

## Hosted and offline CLI

```sh
python3 -B scripts/devtool/cbnx06_lab06_readiness_tests.py
python3 -B scripts/devtool/cbnx06_lab06_readiness.py \
  --source-sha "$(git rev-parse HEAD)" \
  --browser-sha 8012ec00033249566be115e226651c7407ed18c5 \
  --output "$TMPDIR/CBNX06_LAB06_READINESS.json"
```

Optional `--hosted-ui-receipt /path/to/STATUS.json` upgrades only the
source-bound hosted UI evidence flag. Its values can never mark a physical
success. Existing output is not overwritten. This report does not replace
LAB03B read-only before/after, physical manual Iceraven pairing, game data
checks or independent CB-NX07 signoff.

No automatic merge, production install, root write, provider network request,
physical-device action, game file mutation or release is authorized.
