# CB-NX06 LAB03A HF02: emulator case attribution

Source pin `9b43d63e7388c25d9f0a8a2275c88e27c8ef4e91`; PR #89.

HF01 fixed Kotlin compile regressions; all six inherited CI workflows passed. The LAB03A API36-only job booted and installed the emulator test APK, but its receipt was NOT_QUALIFIED without a retained, safe failure reason. The original raw log was deliberately discarded, so no assertion-level root cause is currently proven.

HF02 runs the same two JUnit cases **independently** with bounded 90-second ADB instrumentation timeouts, and requires each case's two status events, `OK (1 test)`, exit 0, and `INSTRUMENTATION_CODE: 0`. The receipt includes only fixed `PASS`/`NOT_QUALIFIED` verdicts and a small whitelisted reason code (such as `TEST_ASSERTION_FAILED`, `TEST_EVENTS_MISSING`, `TEST_TIMEOUT`). It never uploads or prints raw logs, tokens, request IDs, NXM URLs, paths or exception text. An EXIT trap removes both private raw logs.

No test is skipped, faked or auto-qualified. The emulator still refuses installed production package, non-API36, or missing separate lab APKs. Hosted success is NOT physical Android proof, live Nexus acceptance, browser installation, game immutability, mod installation or release qualification.

If the new workflow remains red, inspect the per-case failure label from STATUS.json and apply a targeted runtime fix. Do not relax existing test contracts.
