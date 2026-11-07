# UX-09C02 — actual-device status bar and secondary-screen corrections

Source-pinned to `master` `df382200b6741d58ea8c297d76fa4a1420b0bef3`.
The reference is the user-provided Android 16 screenshots and the immutable approved dark HTML.

- Status-bar safe area is consumed exactly once at the parent NavHost, including Home and secondary routes. Android's bottom navigation inset stays enabled.
- Advanced Mods changes from a cramped toolbar to an explicit Back action, accessible 2x2 action grid and a scrollable empty-library card. Existing import ZIP/profile, backup, update, mod install-review, profile and rollback callbacks are unchanged.
- Steam Login is an optional, concise sign-in screen instead of a large splash. QR, username/password, Steam Guard, resume-session and error flows are retained. The misleading **Continue offline** button is removed; **Back** returns to the pre-existing local app state. No auto-sign-in or implicit entitlement.
- One source-pinned Devtool kit; source transformation verifies individual Git blob hashes before writing. No production business layer, secrets, Steam auth backend, file access or release settings are touched.
- Hosted GitHub Actions API36 tests actual MainActivity routes at 360dp and 393dp, 100% and 200% font scaling, and publishes 12 full-display screenshot candidates including Android status bar.

## Not yet qualified

This is not Steam login acceptance, file write acceptance, approved native goldens, TalkBack, or physical device qualification. The existing Shizuku and live-mod safety gates stay frozen; review dialogs remain explicit. Hosted visual screenshots require independent evaluation after the CI run.
