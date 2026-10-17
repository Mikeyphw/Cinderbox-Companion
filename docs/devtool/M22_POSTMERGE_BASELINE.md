# M22 — merged-source baseline, evidence inventory and roadmap boundary

## Scope and authority

M22 establishes the next development baseline after UI-D01–UI-D03 landed on `master`.
The verified source is `5ba587e2e5b56a054ec38c7c225b50920b304b4c`; its postmerge
GitHub Actions run `39040952179` **succeeded**, with its *own* build provenance.
The M22 overlay creates a **new source commit**. Neither this older successful CI
nor any earlier signed candidate qualifies that new commit.

This milestone performs only read-only host inspection and JSON reporting. It does
not install APKs, touch Android devices, access Steam, inspect private storage,
run device campaigns, or modify save/game/mod data. Its `M22` source inventory
is distinct from M23 real installation discovery and M24 consented downloads.

## Historical evidence policy

The previous 74 M14–M20 passes and M21's 18-case U4/I6/T4/R4 acceptance
are *historical observations*, not passes on current sources. Historical M21
reviewed source: `d93d21d2f569d947bce91099ef112e3b6a793452`.
The original device-local receipts were **not** in the handoff and are not
in this repository. `m22_baseline_contract.json` is a references-only inventory;
it never reconstructs missing original files or assigns invented hashes.
Do not copy or change old receipt results, do not automatically run old campaigns,
and do not relabel successes against the new source.

`m22_baseline.py` produces a versioned evidence report with:
- live `git rev-parse HEAD`, optional matching Actions SHA/ref/run identity;
- SHA-256 of sensitive policy, CI workflows, Devtool targets, M21 evidence code,
  and existing M23/M24 implementation components;
- actual parsed target-local Devtool jobs, wrapper commands and DAG validation;
- historical GitHub run/source anchors and reported observations **as historical**;
- M22–M29 roadmap acceptance coverage and machine-readable open gaps;
- disabled publication, release and automatic device installation flags.

Report `PASS_M22_HOST_INVENTORY` means **this source inspection passed**, not
that M22 new-source CI, original receipts, M23, M24 or full device qualification
passed. `milestone_qualification=INCOMPLETE_ORIGINAL_RECEIPTS_AND_NEW_CI`
remains explicit. A successful later Actions run must be independently verified
and associated with its real checkout SHA and uploaded host evidence. Original
receipt completeness remains outstanding until device owners supply those
original files. Never upgrade an anchor merely from this report's checksum.

## Execution

Use the native Devtool wrapper (Termux-friendly, no Android build):

```sh
./devtoolw m22-check
```

Or run the identical source gate directly and preserve its sanitized output:

```sh
python3 scripts/devtool/m22_baseline.py --output /tmp/cinderbox-m22-host.json
python3 scripts/devtool/m22_baseline.py --verify /tmp/cinderbox-m22-host.json
```

For a complete Android debug build, `./devtoolw m22-full` deliberately reuses
existing Devtool `unit-tests`, `android-lint`, `debug-apk`, and
`verify-debug-apk` jobs; defer real Android compilation to GitHub Actions
rather than invoking this from Termux. Both repo build workflows reuse the
same gate and upload source-bound JSON. No release signing step is added.

## M23/M24 evidence gaps, not yet implemented here

| Gate | Existing module(s) | Unqualified proof |
|---|---|---|
| Package/layout | `InstallationScanner`, `CinderboxLayout` | Installed real game/version, legacy layouts, partial/unknown/corrupt sizes, SAF/root availability without writes |
| Entitlement + manifests | `SteamClientManager`, `SteamContentService` | Licensed real-account depot manifest, consented read-only entitlement |
| Transfer + recovery | `GameDownloadManager`, `GameDownloadService`, `GameDownloadRecovery` | Resumed real transfer and process-death continuation without duplicate commits |
| Integrity + repair | `GameFileIntegrity`, `VerifiedGameRepair` | Hash provenance, space budgets, atomic commit and non-mutating previews |
| SMAPI | `SmapiTransactionalInstaller` | Real compatible installation discovery and migration safety |

All remain NOT_RUN or NOT_QUALIFIED on M22. The roadmap continues unchanged
through M25–M29. Never enable release or publication policy implicitly.

## Provenance update rules

Append new CI receipts/reviews by immutable SHA/run ID; never overwrite the
historical M21 result. Recorded flags for previously resolved source or CI bugs
remain historical, not an excuse to rerun the old campaign. Any Devtool core
issues belong in `docs/devtool/DEVTOOL_IMPROVEMENTS.md` and are fixed upstream,
not by injecting modifications into this app's Devtool installation.
