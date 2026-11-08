# NEX-R3 HF02 — status-backed error presentation qualification

This is a **test-only** NEX-R3 correction, with synthetic offline provider responses, not live Nexus or production auth data.

## Observed hosted failure

On PR #82 at head `c3c38fcc12e16565543e8d645be5a3e6a52c0256`, run 42460839906 passed the real MainActivity Discover→pagination→detail→file review/back and no-key tests. The HTTP 401 error screenshot was captured. The follow-up test's rate-429 transition timed out trying to find the catalog-error text even though a LazyColumn may not have composed the offscreen error panel yet. The sanitized HF01 diagnostic omitted numeric request counters due to an incomplete regex.

## HF02 invariant

Every 401, 429, and 503 scenario must first be observed as a synthetic `OkHttp` interceptor response, then the full Mods LazyColumn is scrolled to the error panel and its actual Compose text verified. A bounded retry accommodates initial compose/layout transitions, but it cannot invent status codes, skip a UI assertion, or claim success on a mock string alone. Capture all three screenshots; retain negative assertions that no mod download was requested.

The runner preserves screenshots taken before failure, emits only bounded status/test information with numeric request counts, and never uploads raw Nexus responses or app secrets. The emulator remains offline at API36 and default font scale. This is **not release approval**, physical device qualification, or authenticated Nexus account acceptance.

Hosted Android compilation and three-case instrumentation must pass on GitHub Actions. No production network, installation, app or UI code changes are included.
