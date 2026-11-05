# M25-02 R1 — Conservative updates and candidate-scoped ignores

Stacked on the M25-01 PR head `434b4beccff337029a7df3556c504a42fca48dee`.
The feature PR targets `feature/m25-01-portable-profiles-notes` until PR #56 merges, then can be retargeted to `master` with no rebase if the parent was merged unchanged.

Implemented:
- Pure version assessment `NEWER/CURRENT/INSTALLED_AHEAD/UNCOMPARABLE/UNKNOWN`, strict numeric and prerelease comparison. Unknown/nonsemver is never automatically an update.
- SMAPI HTTP/JSON failure now throws, so refreshing cannot erase last-known-good cache and pretend no updates exist.
- Exact candidate version ignore in DataStore, bounded validation and atomic writes. A different candidate version resurfaces; ignored candidates remain viewable and reversible.
- Actionable vs ignored lists in Mods; no new bottom tab and no update installation at all.
- Devtool source-only DAG, GitHub JVM matrix, host negative source tests and unchanged R47/R48 hosted emulator gates.

Deferred to M25-02 R2: full per-mod assessment/freshness UI, cache age visualization, long changelog sanitization, broader HTTP-response fixtures, and updated 320dp screenshot qualification. M25-02 R1 is not full milestone acceptance.

Do not add Nexus Collections, automatic downloads, unattended installation, release signing or physical-device claims.
