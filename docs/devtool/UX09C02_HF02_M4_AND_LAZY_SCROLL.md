# UX-09C02 HF02 — M4 contract and native Mods LazyColumn navigation

Pinned PR #76: `4776890ccb7356d4f7848d35c71cb9c395142ac0`; tree `d93baab00edf6902c7b61755a232cdc26b318ba1`.

## Confirmed hosted failures

- Main Build Debug APK: `test_m4_local_first.M4Contracts.test_offline_is_explicit` asserted the old `Continue offline` button exists. The approved newer UX uses a Back action for optional Steam Login. Update the *source regression*, preserving the offline navigation callback and local Settings access.
- UX-09C02 API36: `advancedModManagerHasResponsiveToolbarAndBack` failed on `performScrollTo()` at 786×1704 / 100% font. The `cinderbox.mods.advanced` button is in `ApprovedModsScreen`'s `LazyColumn`; scroll the **container** with `performScrollToNode(hasTestTag(...))`, then click the now-composed button. Keep all other navigation, status-bar, touch, and screen assertions.

This overlay adds only a source-locked patch engine, a fail-closed test suite, and this document. The installer applies the two **existing test-file edits**, validates and commits them with the add-only payload. No production Kotlin, Steam auth, cloud, Shizuku, SAF, root, mod install, release setting, or native golden is changed. The existing user-approved dark reference remains immutable.

Verification boundary: the Python regressions and packaging checks run offline. Full Android API36 execution, 12 screenshots at 100/200% font, and physical-device layout acceptance are pending CI and user-device inspection.
