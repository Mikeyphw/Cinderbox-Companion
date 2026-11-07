# UX-09C01 — real offline text scaling, navigation, keyboard and safe touch targets

Exact source base: `494696b5f0a09c1db6af982a106e568fc7f06bfb` (merged UX-09B4).

This add-only phase runs actual production `MainActivity` in a **disposable, offline API36 x86_64 hosted emulator** at 393×852dp and 360×800dp, density 2.0 and **Android font scale 2.0**. It captures five real tabs at each size (10 native PNGs) and independently tests:

- Every bottom-navigation target is within the Compose root and at least 48×48dp; all five actual tabs can be visited with large text.
- Unauthenticated Steam Cloud and Game download actions remain locked; More → Help → Android back returns to More.
- A real Mods search field accepts keyboard input without routing to Steam authentication or requiring file privileges.
- Actual Compose screenshots and semantic tags match their recorded sizes, retain screenshot diversity and yield machine-checkable provenance.
- The canonical dark palette's main text, muted, faint and selected green foreground/background pairs meet WCAG AA normal-text contrast (4.5:1), calculated from pinned production token colors in source-only tests.

Only the **source-check job** runs offline Python stdlib checks; it never imports Pillow. Builds, APK installation and Android instrumentation run solely on GitHub Actions. The workflow uploads allowlisted screenshots and hash-verifiable JSON metadata on failure or success; raw instrumentation logs are deleted. No images or account credentials are baked into the repository.

**Explicit exclusions:** This phase does not certify TalkBack traversal (requires separately observed screen-reader behavior), 200% compatibility of all 15 deep routes, IME adjustment on every editor, native pixel-parity approval, or physical-device acceptance. The known browser-vs-Android 18dp navigation offset is documented, **not silently removed**. The three UX-09B3 connected/UI fixtures remain illustrative and unqualified as real service authentication. Production Kotlin, GitHub release, Steam entitlement, game writes, Shizuku, root and R2F PR #61 are not changed.

Follow-up phases: broader accessibility traversal / lifecycle restoration / IME insets; data-equivalent test-only renderers and measured safe visual refinements; separately approved native goldens and device acceptance.

## HF01: hosted instrumentation repair

The first UX-09C01 run (42330936561) built but failed AndroidTest before any image was published. The prior driver hid the JUnit output if Android returned shell exit code 0 with failed tests. HF01 now emits a strictly sanitized, non-hidden `UX09C_TEST_FAILURE_RECEIPT_<viewport>.json` containing only test names, known UX09C assertion markers and failure categories. Raw device logs are deleted in both passing and failing cases.

The original Mods test tried to type into search even though the fresh offline emulator has **no Nexus API key** and that input is correctly disabled. Instead the real-app test asserts the disabled state, opens Nexus settings, and types a synthetic, deliberately unsaved value into a real enabled field. No Save, login, credential validation, network authorization, or privileged operation is invoked. The Cloud locked-state check scrolls its LazyColumn before asserting at 200% font.

This remains hosted API36 acceptance only, not TalkBack traversal or physical-device approval. If CI still fails, the diagnostic receipt identifies the failing assertion for a source-pinned follow-up without weakening 48dp touch checks or false green evidence.
