# M25-02 R2 — Status, freshness, inert changelog, API36

This is a **new, source-pinned** R2 slice built from the merge of PR #57 on `master`.
All changes are original Kotlin/Python; Stardrop GPL source was not copied.

- R2 returns observations for every enabled mod. A missing SMAPI record/suggested version stays **UNKNOWN**, never CURRENT. Duplicate case-folded remote identifiers fail closed; current, installed-ahead, newer and noncomparable observations are separated.
- R2 atomically saves a bounded, versioned status snapshot alongside the actionable update cache and successful timestamp; failed requests retain previous observations and expose a stale/failure message. Old cache from before R2 remains supported.
- The Mods UI displays the checked age, category counts and an expandable read-only per-mod list, with disabled/unqueried mods UNKNOWN. Stale installed versions cannot be promoted as current observations.
- Changelog content is capped, stripped to inert text and rendered through a plain `Text` composable. Only explicitly allowed HTTPS update URLs open externally. Changelogs never trigger an installation.
- R2 adds four non-root AndroidTest cases, one private synthetic status screenshot at 320dp/160% font, and a separate evidence receipt in the **existing** R48 API36 emulator job. The existing R48 4-test/5-PNG and M25 R1 4-test receipts remain unchanged.
- No Nexus Collections, automatic mod installation, Steam credentials, real-user data, release signing, root, GameFiles mutation or device acceptance.

## Gates

Host source and negative tests; GitHub `testDebugUnitTest` and `assembleDebugAndroidTest`; R47 11 tests; R48A 4 tests/5 screenshots; M25 R1 4 tests; R2 4 tests/1 screenshot. The R2 receipt is non-release, non-device, and fails if any test, source identity or image digest does not match.
