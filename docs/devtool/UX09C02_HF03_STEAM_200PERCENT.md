# UX-09C02 HF03 — Steam Login accessibility readiness and failure localization

- Exact branch PR #76 at `306071d3b139b18653ec1440a0df69fa00b1cd78`.
- Observed: GitHub-hosted API 36 test succeeds at 393×852 dp / 100% but `voluntarySteamConnectionHasClearReturnToApp` fails `assertExists` at 393×852 dp / 200%. All earlier workflows and production compilation passed. The existing sanitized failure receipt did not identify which assertion.
- Change: retain all original Steam screen, heading, QR and return-to-app checks, but use **bounded 12 s waits** and an individually named failure stage so transient navigation/session-resume timing is handled. No UI assertion is removed, no real authentication is attempted, no credential input is printed and a persistent missing control still fails CI.
- Change: only allowlisted test-stage markers, test-result headings and exception types are carried into the existing sanitized failure receipt. No raw instrumentation logs are uploaded.
- Deliberately **no production code changes**. Local files, Steam credentials, permissions, and release gates are untouched. Approval only after the hosted run produces 12 actual screenshots and successful evidence report. If a stage still fails at 200%, use the stage name to fix the actual UI issue, not to weaken the check.
