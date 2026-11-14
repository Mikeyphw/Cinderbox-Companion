# CB-NX06 LAB03D — private synthetic archive staging and provenance boundary

This source-only milestone follows LAB03C. LAB03B physical acceptance and all live Nexus authorization remain **DEFERRED**. This is not a Nexus Mods download workflow. Neither the browser nor an HTTP caller can invoke staging.

## Operator flow (LAB-only)

1. Build the exact source-pinned `cbnxLab` APK in GitHub Actions. Do not install or update production `com.sdvsync` or the production extension.
2. In the isolated app `com.sdvsync.cbnx06lab`, Settings → Firefox companion → `LAB03D · Private synthetic archive evidence`, tap **Stage and verify synthetic archive (LAB only)**. LAB03A's deterministic archive preview runs first; this button never authorizes network access or mod installation.
3. Staging is performed in `context.filesDir/cbnx06-lab03d-staging/` only, after canonical private-root checks. The source archive/receipt is in `context.filesDir/cbnx06-lab03-synthetic/`.
4. The archive has exactly one synthetic `CBNX06_LAB03_ONLY/manifest.json` member, with bounded size. The existing LAB03A receipt hash must match the byte hash. A second byte-identical staged copy and local-only stage receipt are committed atomically per file (never silently overwritten). The stage receipt records only sizes, SHA-256 and explicit false provenance/install flags; no file paths, Nexus IDs, tokens or URLs.
5. If a staged archive or receipt exists, both are revalidated before reporting success. A partial stage, content drift, symlink, unexpected archive member or corrupt receipt **REFUSES** rather than resetting evidence or touching game data.
6. Source and staged hash matching establishes only **local synthetic byte integrity**. It does **not** authenticate Nexus provider provenance, downloaded file identity, transfer completion, game-folder immutability outside the LAB root, or release readiness. Android runtime and physical acceptance are not claimed by hosted JVM/source tests.

## Qualification

- Dedicated LAB03D workflow: exact PR HEAD, source/negative gate, inherited pairing and consent gates, `:app:testDebugUnitTest`, `:app:assembleCbnxLab`.
- Existing full LAB workflow re-runs LAB03D gates and builds an isolated LAB APK.
- No local Gradle, no production APK install, no live Nexus token/cookie collection, no root, no external Mods writes, no automatic merge/release.
- Deferred: LAB03B pairing/scroll physical proof, LAB03C real browser launch, LAB03D physical staging receipts, LAB04 synthetic install/rollback, LAB05 E2E, LAB06 physical safety, CB-NX07 parity/release decision.
