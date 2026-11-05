# M25-00 + M25-01 R1 — Metadata-only portable profiles

Derived independently from requested Stardrop-like UX functionality; no GPL-licensed code is copied. This phase intentionally excludes Nexus Collections and does not add mod configuration switching.

## Implemented

- Stable UUID profile identity and timestamp, optional description, metadata-only per-SMAPI UniqueID notes, protected flag (not encryption).
- Legacy DataStore profile-array read migration to schema 2, with stable UUIDs and no silent deletion of invalid stored data. An explicit edit rewrites the whole set in schema 2.
- UTF-8-strict import/export format `cinderbox-mod-profile` schema 1, max 256 KiB, max 512 enabled mod IDs, 256 notes with 1,200 characters each, allowlisted fields. No `config.json`, Steam/Nexus secrets, device paths, or mod archives are exported.
- Android SAF `OpenDocument` for import, `CreateDocument` for export. Import only previews missing enabled mod IDs, dependency blockers and proposed toggles; pressing **Save profile only** never installs/applies/renames mods.
- Per-profile note editor, explicit export/import buttons. Protected profile modifications remain refused until explicit unprotect UX is implemented in a later phase.
- Devtool host-only source workflow, Android instrumentation codec fixtures, executed in the **existing R48A API36 emulator job** immediately after its original four real-activity tests. No Gradle in Termux.

## Follow-up and qualifications

- GitHub-hosted debug APK, JVM tests, lint, R47 and the shared R48A/M25 emulator suite must pass on the **exact same PR head**. R48A retains 4 real-activity tests and 5 PNGs; M25 adds 4 metadata-codec tests, separate normalized evidence and independent verification. Compilation alone does not qualify instrumentation.
- M25-01 R2: rename/duplicate/protection UI and full Android acceptance. M25-02: update intelligence. M25-03: bulk mod operations. M25-04: config snapshots only after safety proof.
- M24 Steam download/authentication, R43C production game-file update, release signing, physical device approval and distribution remain independent and disabled.

## Shared hosted-emulator CI architecture (MMRL-LSPosed parity)

- Reuse `.github/workflows/r48-real-activity-acceptance.yml` on Ubuntu 24.04 Linux KVM, pinned `ReactiveCircus/android-emulator-runner@a421e43855164a8197daf9d8d40fe71c6996bb0d` (API 36 / Google APIs / x86_64 / Pixel 6 / 2 cores / 2GiB RAM / 3072MiB disk). No redundant emulator job.
- Existing `r48_emulator_ci.sh` checks exact source SHA, fresh no-account emulator, API36, 320dp/160% typography, immutable APK/test pair hashes, installed app hash and debug signer. The new `m25_emulator_ci.py` reuses the installed pair on the **same** emulator and refuses other devices or changed APK bytes.
- M25 `M25PortableProfileDeviceTest` executes exactly four tests (roundtrip; legacy migration; invalid IDs/schema; invalid UTF8/oversize/corrupt legacy), returns only an allowlisted success/failure summary, and never retains raw logs.
- `m25_verify.py` independently checks four exact test names, terminal status, exit status, source/run identity, independent APK identity, and denial flags. Failed or absent receipts are never promoted to PASS.
- New `m25-profile-api36-emulator-evidence` artifact uploads a bounded receipt even when compilation or instrumentation fails. Historical R48 PNGs remain isolated in `r48-real-activity-emulator-evidence`.
- Same emulator technique is documented by `Mikeyphw/MMRL-LSPosed` S09; **no LSPosed/Vector/root/hook acceptance transfers** to Cinderbox. Neither repository's signing secrets are used.
- Acceptance claims: only hosted-emulator metadata tests are qualified; physical device, real Steam, game installation, TalkBack, live update, signing, and release publication remain denied.

## R1b consolidated audit improvements

- Resaving a named profile preserves its identity, notes and metadata, instead of erroneously refusing the pre-existing update workflow.
- Import preview and notes entry scroll at large Android font scales.
- M25 emulator event acceptance now requires exactly one ordered start/pass pair per method.
- Installer verifies all extracted bootstrap file checksums and refuses drift.

Privacy note: Portable exports do not automatically collect paths or credentials, but explicitly typed profile notes are included verbatim. Review notes before sharing exported JSON.
