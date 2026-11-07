# UX-09D02 — hosted actual-route screenshots, not native goldens

Source-pinned follow-up to PR #77 HF01 `0c85eb3ef2f0a785492d07a2606c54d406c5ec42`.
The 29 workflows for that commit passed. **There was no outstanding CI failure to fix.**

## Additional real Android evidence

Add one dedicated GitHub Actions API 36 job (no local Gradle): actual offline MainActivity at 393dp and 360dp, default font 100%; capture Home, Game, Advanced Mods, Steam Login (without submitting credentials), and Operation Center. Test each route's real click path and return, including Steam Login hardware Back, Advanced Mods explicit Back, and Operations explicit Back. This augments the six already captured Mods/Saves/More screenshots.

Artifacts contain ten PNGs, ten small allowlisted metadata receipts, and a summary JSON with SHA-256, decoded image nonflatness, and sampled light status-bar glyphs. The source-only gate checks emulator prohibition on user devices and missing routes. CI retains preexisting local-first, exact dark reference and safety checks.

No application production source, approved HTML reference, permissions, Steam/Nexus authentication, automatic update/download, game data, accessibility, font size, publication or release policy is changed. No privileged operations are executed. **Not** pixel parity, an approved native golden, physical Android 16 device testing, cloud/save/Steam entitlement qualification or UX-09D02 visual sign-off.

Do not merge until *new hosted workflow* and all required existing workflows pass and the PNGs are inspected. The compositor can still differ from the frozen HTML, especially because browser reference mock data are not real user state.
