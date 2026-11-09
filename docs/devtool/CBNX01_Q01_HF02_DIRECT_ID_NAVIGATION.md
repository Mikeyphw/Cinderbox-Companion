# CB-NX01 Q01 HF02 — direct Nexus mod and file lookup

**Status:** Feature candidate. Hosted CI and real-device acceptance are required. This is a UI/navigation change, not evidence that a Nexus file exists or that browser handoff succeeds.

## Use

1. In the approved **Mods** tab, select **Open by Nexus ID** (available across all four panes).
2. Enter a positive decimal Stardew Valley Nexus **mod ID**. Optionally enter an exact **file ID**. For the initial acceptance exercise the provided values were mod `50535`, file `190561`; a later Iceraven banner displayed file `178239`. They must be treated as distinct tests, not interchangeable IDs.
3. Select **Open exact selection**. It navigates to the approved native details screen without downloading or installing anything.
4. If a file ID was entered, an exact-file panel appears at the top with a name and buttons **only if that file ID occurs exactly once in the loaded Nexus provider file list**. If missing, duplicated, or failed to load, no substitute actions appear.
5. The existing **Files & versions** section now displays each numeric provider file ID and includes an exact-ID filter for manually finding a file without scrolling through other versions.
6. An explicit **Open exact file in Iceraven** button opens the existing strict browser handoff URL; an explicit **Download exact file for review** starts the unchanged guarded download path. Navigation alone starts neither.

No new tab, WebView, browser authentication shortcut, forced download, bypass of Nexus requirements, or change to the existing mandatory ModReviewQueue approval.

## Qualification

The GitHub CI suite must pass the existing source, JVM, Android36 instrumentation, UI, and screenshot checks. Physical acceptance still requires a matching CI debug APK and a real Iceraven-to-Cinderbox archive staging observation. Merely entering IDs is not a substitute for actual file identity provenance.
