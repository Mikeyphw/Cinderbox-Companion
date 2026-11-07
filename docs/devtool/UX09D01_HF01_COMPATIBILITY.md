# UX-09D01 HF01 — legacy source contract and hosted screenshot compatibility

Source-pinned to PR #77 `724b2c0a41a249089531c84c15c8e6674a55958f`.

## Observed hosted failures

- Several UX-05 through UX-09A source checks require the old literal "Your mods" and old manager CTA, despite the approved UX-09D01 production title being "Mods" and "Manage local mods".
- R48 hosted Android instrumentation also requires the old literal title. Instead, the test now checks the unique existing Mods-page subtitle "Discover, organize and customize." while the UX-05 source gate checks the **exact** new title expression.
- UX-09B4's visual sampling checks only a narrow screen-center grid. In run 42400362243 it rejected `mods-profiles-360` despite the actual PNG visibly containing text, cards and buttons. The sampler now covers the full content band and independently requires foreground pixels; blank or flat images continue to fail.

## Safety and limits

This changes only source contracts, two instrumentation expectations, and test-image sampling. It does not change production Kotlin, authentication, filesystem safety, release flags, live updates, approved browser references, or device privileges. No native golden is approved. Hosted R48, UX-09B3 and source safety workflows must pass on the new commit.
