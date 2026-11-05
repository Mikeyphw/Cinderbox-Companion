# M25-03 R1 — Grouping and selection (read-only plan)

**Parent:** Cinderbox Companion `master` at `dec044416fc3c563e91fc3d93dca06b7cf4ac8d2`.

## Implemented

- Mod list group controls: all, author, SMAPI mod, content pack, update attention and compatibility warning.
- Search and existing enabled/disabled/update filters still combine with grouping. Author grouping sorts deterministically.
- Explicit multi-select, select-visible and clear, with counts and names; changing search/filter/group clears selection.
- Read-only bulk enable/disable preview with requested IDs, steps, metadata fingerprint, dependency blockers and folder-collision warning.
- No action executes the plan. No nontransactional multi-mod toggle loop was added. R43 transaction and release gates remain unchanged.
- New host Devtool job, source checks, separate GitHub JVM tests, existing debug/R47/R48 hosted CI on PR changes.

## Deliberate limits and R2 entry criteria

The plan fingerprint is based on installed manifests and folder names and is NOT proof of current directory bytes, symlinks, launch-state, or journal state. The R1 screen is a preview only; it does not offer confirmation that mutates mod folders. M25-03 R2 must re-read an independently validated Mods root, check symlinks, source/target collisions, stale or pending journal, game-launch constraints, and then apply **one** journaled all-or-rollback batch. Use failure injection and byte-preservation tests on disposable CI fixture roots before exposing live enable/disable actions.

Do not add Nexus Collections, release signing, physical-device claims, `pm clear`, uninstall or automatic installations.
