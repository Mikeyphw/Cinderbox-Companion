# UX-09C02 HF04 — Steam entry action at 200% font scale

## Hosted failure and scope

On PR #76 SHA `469e0f61a022d23202f116c91db6a4287def658e`, run
`42384016585`, the hosted test failed at stage `steam-screen` for
`786x1704` / 200% text, after the test found the Home Steam button. The
same scenario passed at 100%. The Home CTA is inside a `verticalScroll`
container, so existence in the Compose semantics tree does **not** prove
that its touch target is visible. Off-screen click coordinates can fail to
navigate.

## HF04

Before tapping `cinderbox.steam.connect`, the test now performs
`performScrollTo()` and `assertIsDisplayed()` in a separate, named
`home-connect-visible` stage. A missing target, failed scroll, failed click,
absent Steam screen, Steam QR button, or Back return still FAILS CI. Bounded
existing stage waits remain at 12 seconds; no skip, mock login, or fake
navigation is introduced. The hosted source workflow explicitly executes
new HF04 negative regression tests.

## Qualification and scope boundaries

Changes are limited to a hosted Android instrumentation test, a CI workflow,
and three add-only documentation/patch/testing files. No production Kotlin,
Steam credentials, installed mods, file writes, release configuration,
approved reference HTML or R2F Shizuku source is changed. The test does not
perform Steam authentication. Hosted API36 rerun must pass all 12 screenshots
before PR #76 is ready for review, and device screenshots remain an independent
acceptance check.
