# UX-00–UX-02 implementation checkpoint — approved 2026-11-06 dark

## Implemented in this checkpoint

- Opens nested `main` → `home` on first launch. Existing `login` stays available **on explicit Steam Connect**, but never gates the app. Sign-out returns to Home. Logout does not clear local saves/mods.
- One approved dark style (`#101915`, `#1b2922`, `#8cd9a8`, etc.). The old appearance selector is gone; More displays **Dark · default**. Historic style type names survive only for source compatibility, not as user selectable modes.
- Shared 5-tab modern bottom bar with fixed order and tags. Home provides approved responsive hero landscaping, optional Steam card, glance cards, quick actions, activity entry, dedicated local-first copy. No demo save counts or fictitious history in native UI.
- Pure authorization presentation policy models Steam sign-in, entitlement, network, cloud independently. A UI `AVAILABLE_FOR_FURTHER_CHECKS` response never grants game-file write permission. Existing Steam download/service authorization still applies.
- Frozen HTML single-dark reference + 24 Chromium portrait goldens + machine contract, active browser reference CI and initial native build CI.
- R44 old appearance checks are updated to require the new dark singleton. Existing release locks, M25/R47/R48 security checks are preserved; R47/R48 historical UI test assumptions are adapted to local-first entry points.

## Not yet accepted

UX-02 Home live counts and recent activity adapters; UX-03 Game; UX-04 Saves; UX-05/06 Mods; UX-07 More parity; UX-08 deep screens; UX-09 Android screenshots/a11y and complete UX qualification. This is **not** a proof of visual Android parity. Native screenshot goldens must be accepted separately. Historic test screenshots named classic/earthy are compatibility fixtures only and do not enable alternate appearance modes.

R2F PR #61 remains separate. The UI patch never changes GameSessionSafety, mod bulk source/destination policy, release gates or Shizuku R2F files. No physical install is performed. Real live Mods bulk writes remain explicitly disabled.

## Execution

Run from Termux with `zsh APPLY_UX_FOUNDATION.zsh`. The runner refuses a moved `master`, divergent branch, dirty checkout, changed source hash, or non-fast-forward remote. It generates a single exact-tree Devtool overlay, applies it transactionally, commits and pushes the new feature branch and creates a PR. Gradle and Android emulator work run on GitHub Actions, not in Termux.
