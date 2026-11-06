# M25-03 R2D — Explicit game-process diagnostic, fail-closed

PR #60 continues from R2C SHA `23dfa3c554b6f5acd457d2c17556c875f2dd3541`.

**Safety boundary:** Live bulk enable/disable is still disabled. A root-capable `pidof`
scan, even when double-checked with `ps`, is a point-in-time observation, NOT proof
that the game cannot launch or change its Mods folder during a transaction.

R2D adds a small, optional **Check game status** action to the existing bulk preview.
It triggers a bounded root process inspection only when requested. Statuses:
`RUNNING`, `NOT_OBSERVED`, and `UNKNOWN`. Any root denial, timeout, parsing error,
or unavailable command is `UNKNOWN`. Neither `NOT_OBSERVED` nor any other result
permits live bulk changes; `GameSessionSafety.permitsLiveBulkWrite` remains false.

The preview remains read-only, its original title is retained for R1 compatibility,
and the existing R2C fixture-only commit API is untouched. Diagnostic results are
cleared when the preview is dismissed or regenerated; no raw process output is
saved, transmitted, or logged. Never silently grant root in the background.

Acceptance: 8 JVM tests, the new R2D source contract, R1/R2A/R2B/R2C gates, hosted
APK compilation, R47/R48A UI emulator workflows triggered by screen changes.
No physical-device, TalkBack, release, publishing, or real Mods write claims.

**Later milestone:** live writes require separate authorized real-device evidence
and a stronger game-session handoff/idle condition; a negative process snapshot
alone is not enough. Do not treat the existence of `su` as user permission to
modify Mods.
