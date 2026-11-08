# NEX-R3 — native MainActivity end-to-end navigation acceptance

## Source and evidence provenance

This milestone is **hosted acceptance only**. It changes no production app code,
network API implementation, download pipeline, login flow, UI typography, theme,
permissions, root/Shizuku, or release policy. It adds a source-pinned Android test,
a fail-closed offline emulator runner, PNG evidence verifier and GitHub workflow.

The credentialed live NEX-R2C provider check passed independently in GitHub run
[42446450123](https://github.com/Mikeyphw/Cinderbox-Companion/actions/runs/42446450123),
head `d62be3dddd759b67e436cdcfa3285c35c25035ff`. Its status receipt verifies
provider API shape but is **not** an Android E2E, user-account, or download test.

The NEX-R3 Android test launches the **real MainActivity**, with a Koin-injected,
**test-only** `NexusModSource` configured with a local OkHttp `Interceptor` that
cannot reach the network. A synthetic non-secret API-key sentinel lives only in
the fresh emulator's encrypted preferences and is deleted by the test teardown.
The test refuses any existing Nexus API key, forbids unexpected URL/host/path,
and never issues a download-link request. No fake provider data is sent to Nexus.

## Acceptance cases, 360dp and 393dp at 100% font (API 36)

1. Discover first server-owned page, load second page via real UI (GraphQL offset
   50), open a mod, view native details, explicitly enter guarded file review,
   go Back twice, and preserve read-only behavior.
2. Trigger HTTP 401, 429 and 503 responses from the local fixture through the
   real provider error mapper. Confirm no phantom results or download requests.
3. Remove the synthetic test key and verify local Mods still opens and prompts
   for Nexus access without any provider traffic.

Screenshots are real Compose/MainActivity screenshots **of synthetic fixture data**.
They are not a Nexus account capture, approved pixel goldens or
physical-device qualification. `nex_r3_evidence.py` requires exactly 18 PNGs,
PNG signature/IHDR, exact 360/393 source-bound viewport dimensions and a SHA-256
for every screenshot. The JSON receipt contains no real Nexus data or secrets.

The runner refuses non-GitHub hosts, non-emulators and unexpected Android API
levels; reuses R48A strict airplane/default-network isolation rather than `svc`
commands. No source or device write path grants installation permissions.

## Gates

- Source, negative regression tests and image integrity tests run on PR.
- Hosted Gradle compiles both APKs; the runner installs only on a fresh GitHub
  API 36 emulator and uses `am instrument` with exactly three tests at each size.
- Existing app-wide workflows remain required on the changed PR HEAD.
- Source/JVM/real navigation pass is not release approval. Physical-device,
  real-user account, download/install, signing and publication tracks remain
  explicitly out of scope.
