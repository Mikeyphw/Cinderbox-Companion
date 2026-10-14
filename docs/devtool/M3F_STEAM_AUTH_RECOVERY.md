# M3F — Steam authentication recovery (candidate; not a release)

## Incident

On rooted Android 16, both credential+email-code attempts connected to Steam CM over TCP, then disconnected about 30 seconds later while the login UI remained on **Authenticating**. The app does not report a wrong code. The source already tries to surface disconnections, but a completed/cancelled attempt can leave an orphaned transient UI state.

## Changes

- Prefer `StableWebSocketConnection` for the *initial* Steam CM transport, with the pre-existing TCP transport as fallback on initial connection failure. Do not switch transports within an in-flight authentication session, which would invalidate that session.
- Add bounded waits: initial credentials request 45 seconds, Steam Guard submission 45 seconds, all Steam authentication polling 120 seconds, final Steam login callback 30 seconds (including session resume).
- Convert these timeouts into a visible, localized retryable error, then shut down the transport for the next attempt. Steam Guard's **waiting for user entry** remains unbounded; no code is auto-submitted or saved.
- Restore a visible disconnect error if an active coroutine has finished/cancelled while a transient login state is still displayed.
- Update the existing TCP/WSS plan tests; add unit tests for the orphaned-state recovery policy and Python source-regression tests.

## Limits and next steps

- This repairs a known error path but is **not** proof of Steam login success. GitHub Actions must run `testDebugUnitTest`, `lintDebug`, and build the APK; actual Steam authentication requires a device with authorized credentials.
- The candidate/Gradle build must be signed by the user's existing private signing key via GitHub environment and protected workflow. Do not install a debug APK over a release-signed APK.
- If Steam still disconnects on WSS, capture sanitized `SteamAuth` and `SteamClientManager` logs; do not disclose Steam Guard codes, passwords, access tokens, or session files.
- Do not change release qualification, publisher, or auto-install flags.
