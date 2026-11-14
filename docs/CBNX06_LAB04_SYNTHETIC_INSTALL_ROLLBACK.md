# CBNX06 LAB04 — Synthetic app-private installation and rollback

Status: SOURCE IMPLEMENTATION ONLY. LAB03B physical pairing remains deferred, and hosted CI cannot qualify physical install, rollback, Nexus origin or Iceraven extension behavior.

The LAB04 panel is present **only** in `com.sdvsync.cbnx06lab` with the private game root `filesDir/CBNX06_GAME_LAB/desktop/Mods`. The production `com.sdvsync` paths and NXM behavior remain unchanged.

## Operation contracts

1. The user explicitly taps **Install synthetic mod (LAB)** and confirms the dialog. No remote/browser action can enter LAB04.
2. The private LAB Mods root must contain **zero** entries; the receipt must not already exist.
3. LAB03D staging re-verifies the synthetic generator/source receipt, deterministic ZIP member and source/staged SHA-256. The real `ModFileManager.previewFromZip()` must offer exactly one **ADD** of folder `CBNX06_LAB03_ONLY` with ID `CBNX06.LAB03.Synthetic`.
4. A durable `INSTALLING` receipt is written before `ModFileManager.installFromZip(stagedZip, approvedReviewKey)`. The result must contain one mod and only the exact expected synthetic manifest bytes.
5. The user explicitly taps **Rollback synthetic mod (LAB)** and confirms. The receipt must say `INSTALLED`; staged ZIP bytes and the sole installed mod's manifest must match exactly. `ModFileManager.removeMod()` retains a snapshot and removes only that one folder. The root must become empty.
6. Persist `ROLLED_BACK`; the receipt remains, so this intentionally cannot silently reinstall or run multiple rounds.

## Refusal cases

Corrupt/partial stage; missing or malformed receipt; altered target; other mods in root; symlink; bad source SHA; another app package; repeated install/rollback; crash in `INSTALLING`/`ROLLING_BACK`; no accepted review; post-install content drift all **fail closed**. Do not delete journals, clear application storage, or manually remove game files to force a pass. An interrupted state requires manual engineering review.

The synthetic ZIP is **not** a Nexus download. LAB04 does not use HTTP, real Nexus credentials, the production game Mods directory, Android root privileges, or a release pipeline. A completed hosted JVM build establishes source/build qualification, not physical device acceptance.

## Later milestones

LAB05 covers full isolated UI + Iceraven E2E and LAB06 physical safety/restore. Those remain deferred independently of GitHub CI. CB-NX07 is the separate final parity and release decision.
