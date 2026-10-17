# M21 — Consolidated Feature Completeness & Release Readiness

## Exact source and scope

- Source baseline: merged M20 `feafc8a0fdd3ea2662a168a78e2ba091f0a25d7e`.
- Intended feature branch: `feature/m21-feature-release-readiness`.
- One PR and **one pre-existing GitHub debug/instrumentation build**, with an M21 host regression step. Never build or publish a release artifact in CI.
- All 74 earlier Android cases are **historical PASS evidence** from M14–M20. Their tests are not executed by this M21 runner. M21 has a new, separate, 18-case manifest.
- No credential acquisition, forced Steam login/logout, save/cloud upload, download into user folders, arbitrary game install, uninstall, data clear, reboot, or automatic publication.

## Four independently executable lanes (18 new cases)

| Lane | New cases | Claims when PASS | What it does NOT prove |
|---|---:|---|---|
| U · Real offline user workflows | 4 | Real signed-out Compose navigation for Saves, Mods, Downloads, and installation-health information | Real Steam data or authenticated workflow |
| T · Authenticated Steam read-only | 4 | Previously logged-in encrypted session present, live Steam connection, license callbacks and genuine Steam Cloud metadata enumeration | Steam download authorization, cloud upload, game/saves restore, Steam Guard QR challenge |
| I · Installation recognition and replacement | 6 | Synthetic game-tree recognition, actual Cinderbox package recognized, and private test marker survives consented same-signature APK replacement | New release certificate upgrade, real game/SMAPI installation, external filesystem migration |
| R · Release APK cryptographic checks | 4 | Independently SHA-pinned release candidate, separate release certificate vs signed CI debug APK, valid APK signature, correct non-debuggable package | Store publication, signature migration of an existing debug install, distribution policy/legal approval |

T intentionally requires a currently authenticated profile and user-initiated sign-in. U requires a signed-out profile. **Do not sign in or out as an automated test step.** The operator transitions between profiles manually; the runner never clears application data or creates credentials. Steam Cloud enumeration is read-only, and reports contain neither file names nor counts from the user account.

I requires the actual separately installed `com.game.cinderbox` package to be present. If it is not, I **fails explicitly** rather than substituting a synthetic package for an actual installation. A successful test installation verifies the pre-existing application's package identity; it does not modify that game's files or packages. The consented Companion APK `-r` test is same-signer, same-build data-preservation only; it does not claim an upgrade between distinct release versions.

R requires a locally supplied, separately signed release APK and **independently obtained** SHA-256, release signer certificate fingerprint and pinned debug signer fingerprint. The source-bound runner verifies the debug certificate pin against the actual CI debug artifact. The release candidate is **never installed or published** by R; signing, release artifact creation and the distribution decision are outside this overlay. No artifact or signer pin means R remains NOT_RUN, never PASS.

## Evidence policy and run sequence

The existing `M3_PROVENANCE.json` and `M13_QUALIFICATION.json` are required; M16 signatures on both CI APKs remain required. The new runner verifies CI checkout/ref, PR commit, byte hashes, branch, all M21 host gates, Android ABI/API, individual method passes and exact manifest coverage. Only the intended M21 test methods run, never M14–M20.

**1. Inspect the four lanes:**

```sh
python3 scripts/devtool/m21_campaign.py --list-lanes
```

**2. Signed-out, offline and installation lanes** (with no active operations and installed `com.game.cinderbox`):

```sh
python3 scripts/devtool/m21_campaign.py \
  --run-id <M21_CI_RUN_ID> --transport termux-root --lane U,I \
  --ui-opt-in --signed-out-opt-in --installation-check-opt-in \
  --upgrade-opt-in --install --allow-replace \
  --output "$HOME/cinderbox-m21-UI.json"
```

**3. Authenticated read-only lane** (only after user signs into Steam through normal app UI, confirms no active jobs):

```sh
python3 scripts/devtool/m21_campaign.py \
  --run-id <M21_CI_RUN_ID> --transport termux-root --lane T \
  --ui-opt-in --authenticated-opt-in --install --allow-replace \
  --output "$HOME/cinderbox-m21-T.json"
```

Do not expect T to succeed while signed out. The test does not use, print, copy, persist or return an account credential. If an account has no licenses, T03 fails as unavailable qualification evidence rather than guessing.

**4. External locally signed release APK** (with operator-supplied out-of-band pins):

```sh
python3 scripts/devtool/m21_campaign.py \
  --run-id <M21_CI_RUN_ID> --release-audit --release-audit-opt-in \
  --release-apk /absolute/path/to/SIGNED_RELEASE.apk \
  --release-apk-sha256 <INDEPENDENT_SHA256> \
  --release-cert-sha256 <OUT_OF_BAND_RELEASE_CERT_SHA256> \
  --debug-cert-sha256 <M16_CI_DEBUG_CERT_SHA256> \
  --output "$HOME/cinderbox-m21-R.json"
```

The tool requires `apksigner` and `aapt`. Never create or copy the signing key into this report or repository.

**5. Consolidate source-identical reports:**

```sh
python3 scripts/devtool/m21_campaign.py \
  --merge-reports "$HOME/cinderbox-m21-UI.json" "$HOME/cinderbox-m21-T.json" \
                  "$HOME/cinderbox-m21-R.json" \
  --output "$HOME/cinderbox-m21-final.json"
```

The report becomes `PASS_M21_PREPUBLICATION_ACCEPTANCE` only when U, T, I, R all pass, same source/CI/APK hashes match, and real device reports refer to the same device. A partial or blocked scenario cannot count as PASS. `publication_allowed`, `release_qualified` and `device_qualified` deliberately remain **false**; a separate release decision is required.

## Security and release findings

- `SteamCloudService` previously logged Steam Cloud filenames, path prefixes, machine names, batch identifiers and decoded save-content excerpts. M21 removes these raw-value diagnostics; it does not remove the functional metadata/API fields.
- Distinguish a valid pinned M16 **debug** certificate from the operator-controlled **release** signer. An APK signed with the debug certificate is not a release candidate.
- Release configuration currently expects an external `keystore.jks` and passwords. This overlay neither provisions a release keystore nor requests secrets. A release APK must be built/signed separately and independently verified.
- M21 is an acceptance/prepublication audit, **not** permission to publish. User-workflow compatibility across more Android devices, authenticated download/write paths, key-rotation handling, privacy-policy compliance and real store policy remain distinct future obligations.

## Evidence history / risk

M20 native Android 52/52 PASS, real force-stop and cold relaunch confirmed, CI `38926722038`, PR #25 merged. Prior M14–M19 22 milestone-specific passes preserved. M21 does not reexecute those suites. No manual or credential-dependent lane is silently skipped or treated as a pass.

## M21 AndroidTest compilation hotfix (2026-10-16)

- Source: M21 PR #26 at `ac0c0f7d3d61b5a16ae572ee06e8bfa7e15b35d2`, GitHub Actions run `38940534401`.
- CI application build, M16 APK signer verification, and M21 host regressions succeeded; instrumentation compilation failed at `app/src/androidTest/java/com/sdvsync/qualification/M21ReadinessDeviceTest.kt:5:33`: unresolved import `androidx.compose.ui.test.assertExists`.
- `SemanticsNodeInteraction.assertExists()` is a member; delete **only** that invalid import and preserve the existing `.assertExists()` checks. Host tests now enforce the source contract.
- This is a **compile error**, not device evidence or an authenticated Steam failure. Do not run M21 devices against run `38940534401`; qualify only after a new source-bound CI run successfully compiles, signs, and uploads `m14-androidtest-apk`.


## M21 completion and integration (2026-10-16)

The prepublication acceptance receipt on the reviewed commit
`d93d21d2f569d947bce91099ef112e3b6a793452` is
`PASS_M21_PREPUBLICATION_ACCEPTANCE` with 18/18 current cases PASS; 74
historical M14–M20 cases remain preserved without rerun. Android API 36,
arm64-v8a, CI debug run `38946596038`, synthetic checkout
`dc7439617acaa10823a5e9bc95091bf8771f21f2`.

A **separate, manual, non-publishing** GitHub Actions release-candidate
build `38964234525` verified `:app:assembleRelease`, signature, distinct
release certificate, non-debuggable package, and artifact publication to
GitHub Actions artifacts only (not app distribution). Release candidate APK
SHA-256: `8ad0de78abd3791d2c709ebcb17c2d78240c4038a301110643cdacd6605bc5f6`.
Its signer SHA-256: `1a97bfe73fccba607b7816e50db0fa1c16850b3036c4bb156efe047e70046ca0`.

M21 release audit recovered two tooling problems without altering that
reviewed commit: GitHub may report a null live open-PR `merge_commit_sha`
even when its signed CI receipt and historical merge Git object agree, and
Termux `apksigner` can produce a valid signature with console text the
original parser did not recognize. This follow-up integrates fail-closed
checks into source (signed artifact provenance + exact Git ref/parents,
`apksigner verify` + binary certificate extraction).

**Qualification boundary:** Historical 18/18 acceptance applies to the
original reviewed source/CI/APK. Reconciled integration commits require their
own GitHub CI. They must not retroactively rewrite acceptance receipts or
claim release_qualified/device_qualified/publication_allowed = true.
