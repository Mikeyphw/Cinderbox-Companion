# UX-09B4 — consolidated safe-area / 24-case visual geometry evidence

**Exact base `master`:** `f3c3fd2ab3d1564bdd1a785ad127491c02bb764a`.

## What changed

1. Isolated test Compose fixtures apply `WindowInsets.statusBars` to both the two-tab presentation shell and Mod Detail. Captures now assert that semantic screen roots begin below the status bar (40–120 **physical pixels** at 320 dpi) before accepting screenshots. This does not alter real `MainActivity` insets.
2. The existing hosted API36 UX09B3 job continues to capture **21 real MainActivity offline states** and **3 distinct isolated presentation-only states**. It now runs `ux09b4_visual_audit.py` after the 24-case receipt and publishes `UX09B4_VISUAL_AUDIT.json`, `UX09B4_CASE_MATRIX.csv` and `UX09B4_VISUAL_REVIEW.md` alongside unmodified PNGs/diffs.
3. All 24 native/reference PNG hashes and dimensions are rechecked. The three fixture JSONs must provide measured native content-top boundaries and must declare no authenticated Steam, Cloud, catalog, file or privileged state. Whole-frame and reference-content-band RGB differences are measured **for diagnosis**, not acceptance. The report explicitly flags the known ~18 dp difference at the bottom navigation.
4. Host source contract, negative tests, prior UX09B3–UX08C safety gates remain. No Gradle runs in Termux; CI builds on GitHub.

## What is NOT approved

No physical device acceptance, Steam ownership, cloud data, real mod catalog, live update / bulk-mod writes, release signing, publication or UI pixel parity. The three fixtures use test-only presentation flags and sample mod data, **not** a mocked authenticated MainActivity.

The user-approved HTML and 24 browser golden screenshots remain untouched. Android system bars are preserved in native captures. The content-band metric excludes only the browser-specified status/bottom-navigation rectangles and does **not** compensate or crop the original native PNGs. The 18 dp navigation difference cannot safely be 'fixed' by removing Android's `navigationBarsPadding()` without a device-safe UX decision.

## Next after green hosted CI

Review the 24 comparison PNGs, align fake reference content and real Android test fixtures in a separate test data source (no production synthetic accounts), and submit a separate native-golden approval step. Do not enable strict pixel-parity CI until native goldens have been inspected and expressly approved. Proceed then to UX-09C accessibility, text scaling, IME, lifecycle and M25/R2F qualification.
