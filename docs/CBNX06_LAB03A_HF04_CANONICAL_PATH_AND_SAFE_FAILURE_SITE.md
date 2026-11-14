# CB-NX06 LAB03A HF04 — canonical private evidence path and safe failure site

Source-pinned PR #89 parent: `80e22f6c46a3ac796c0de48043d4a58f892eb703`.

## Concrete source defect and correction

`CinderboxLabBoundary.initialize()` sets `privateHome` to `context.dataDir.canonicalFile`.
The synthetic evidence helper, however, constructed its child directory directly
from potentially aliased `context.filesDir`. On Android, `/data/user/0` and
`/data/data` may name the same private storage while having distinct raw path
prefixes. `requirePrivate` intentionally checks the raw path against the canonical
root *before* its own canonical-path check. A same-app alias can therefore be
rejected with `LAB_PATH_ESCAPES_PRIVATE_DATA` before archive generation begins.

HF04 constructs the evidence directory from `context.filesDir.canonicalFile`.
It preserves `requirePrivate` unchanged; no link exception, broader storage
permission, external game path, production package, mod install or downloading
is introduced. This is the most direct source-backed candidate for the failing
`syntheticArchivePreviewDoesNotModifyLabMods` test. The exact pre-HF04 exception
is unavailable because CI correctly deletes raw logs.

## Bounded fail-closed diagnostics

The existing two instrumentation tests, `AndroidJUnitRunner` final result
contract, 90-second per-test timeout, Android API36-only emulator gate and
private raw-log cleanup are unchanged. On failure, the receipt now records only
an allowlisted **Kotlin source filename basename and numeric line number**
from AndroidJUnitRunner's error stack (`failure_site`), or `UNAVAILABLE`.
No exception message, raw stack, Nexus token, download URL, filesystem path or
payload is emitted. `TEST_ASSERTION_FAILED` is never converted into a pass.
Source/negative regression tests enforce the canonical path and redaction.

## Qualification and scope

Host/Termux only applies source patches in a disposable `$TMPDIR` clone after
exact SHA/blob verification, runs inherited Python gates, makes a non-force
push to the existing PR branch and shows fresh exact-SHA GitHub CI checks.
Gradle and API36 emulator execution occur **only on GitHub Actions**. If LAB03A
still fails, inspect its new redacted receipt `failure_site` before further changes.
LAB03B, physical ARM64 Android, real Iceraven extension installation, production
immutability and release remain **NOT QUALIFIED** until separately proven.
