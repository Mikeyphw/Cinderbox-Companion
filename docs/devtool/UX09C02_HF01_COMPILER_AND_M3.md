# UX-09C02 HF01: Kotlin AndroidTest import + M3D Settings contract

Pinned branch head: `526e9cbdf672e7bb2904320dd93f9af1f4998552`.
Pinned tree: `7d3726f1cc2dcabe93bf686b9c07f22365eefcb7`.

The first hosted execution of PR #76 failed because `UxDeviceChromeTest.kt`
imported `androidx.compose.ui.test.assertExists`, which is not a valid top-level
import in the project's Compose version. `assertExists()` is already available
as a member of the `SemanticsNodeInteraction` returned by `onNodeWithTag`.

The existing M3D pre-login regression also expects the localized Settings title
in Steam Login; the UI overhaul had replaced it with an English string. Restore
`stringResource(R.string.settings_title)` while keeping the Back action and removing
`Continue offline`. The Settings action remains available without authentication.

The installer first applies an exact-tree Devtool add-only payload, then performs
only those two exact Git-blob-preimage-guarded text replacements, validates the
source gates and regression tests, stages exactly five paths, and commits/pushes
back to the same PR branch. No production auth, mod-write, root, Shizuku, release,
reference, or service files are altered. Hosted Gradle and API36 remain mandatory.
