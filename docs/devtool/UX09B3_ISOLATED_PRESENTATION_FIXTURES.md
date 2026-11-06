# UX-09B3 — 24 screenshot candidates; **NOT** 24 approved native goldens

Source-pinned to UX-09B2 merge commit `98a7df24cf2b2a23c8e37af42e54c42b2d7d5c02`.

## Precise qualification boundary

UX-09B2 proved that 21 HTML-reference states can be captured from the **actual, logged-out, read-only MainActivity** on a hosted API36 x86_64 emulator. UX-09B3 retains that pipeline without modifications, and captures the remaining three images by rendering the **existing** production Compose UI composables under an isolated Android **test-only UI fixture**:

| Browser reference | Fixture mode | Explicit limitation |
|---|---|---|
| Game — Steam connected | ApprovedGameScreen, `isSteamConnected=true` UI preview | Does **not** create a login, entitlement, session, proof of ownership, or service permission |
| Saves — Steam Cloud connected | ApprovedSavesScreen, `isSteamConnected=true`, cloud tab selected | Does **not** connect to cloud or synthesize a save inventory; actual service stays offline |
| Mod detail | ApprovedModDetailContent with in-memory `RemoteMod` and `ModRequirementsAssessor` UNKNOWN | Not real provider metadata, not a verified installed mod, no download |

The three cases are **visual snapshots of isolated production composables**, not MainActivity navigation acceptance. No production Kotlin classes, Steam auth providers, filesystem logic, root or Shizuku services are patched. The approved browser HTML and 24 screenshot/layout references are unchanged.

## Evidence and safety

The hosted job builds debug + test APKs, verifies a real emulator (`ro.kernel.qemu=1`, API36, serial `emulator-5554`), disables emulator data and Wi-Fi, reruns UX-09B and UX-09B2 for 21 real screenshots and generates the three fixture screenshots. The report validates each origin separately, includes SHA256 hashes and comparison triptychs, and explicitly records:

- `actual_real_activity_cases: 21`, `isolated_preview_fixture_cases: 3`
- `all_24_states_covered_as_screenshot_candidates: true`
- `full_24_case_parity_verified: false`, `native_goldens_approved: false`
- `real_steam_auth_and_entitlement_qualified: false`, `real_mod_catalog_qualified: false`
- `physical_device_qualified: false`, `live_mod_bulk_writes_enabled: false`
- `release_enabled: false`, `publication_enabled: false`

A screenshot match can **never authorize** a file operation, Steam/Nexus access, new golden, installation, release, or user-device qualification.

## Pending UX-09B4 / UX-09C

1. Compare **equivalent in-memory inventory data** at 393 and 360 widths without making release fixtures or network requests.
2. Fix measured Compose-vs-browser navigation inset (the 17-case UX-09B baseline showed 18 dp nav-top delta), typography, responsive bounds and overflow in production via separately source-reviewed functional patches.
3. Independently review, name and pin **native-only** goldens after design acceptance. Then make native screenshot and semantic-geometry drift hard failures, with explicit tolerances grounded in Android rendering.
4. UX-09C: accessibility content descriptions, 48dp tap targets, 200% font scale, keyboard/IME, orientation and lifecycle/process recovery.
5. Real Steam auth and cloud, R2F Shizuku acceptance, live filesystem transaction recovery and physical device acceptance remain separately gated.

Never interpret UX-09B3 screenshot coverage as complete UI fidelity or Steam/physical device qualification.
