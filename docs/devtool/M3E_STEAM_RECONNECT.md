# M3E — Steam connection-aware game branch loading

M3E repairs the Download Game screen failure observed on Android 16 when a saved Steam session temporarily disconnected. The production trace was `SteamAuth: No network available`, then `AsyncJobFailedException` at `SteamApps.picsGetAccessTokens(...)` while looking up Stardew Valley's branches.

## Changes

- Watch `SteamClientManager.connectionState` and require `LOGGED_IN` before enabling Steam game downloads.
- On first navigation, wait up to 7 seconds for ongoing Steam reconnection; do not start a new authentication attempt automatically.
- On user-initiated **Reconnect Steam & Retry**, use the existing saved-session mechanism if not already reconnecting. Wait up to 30 seconds for `LOGGED_IN` before making a PICS request.
- Block overlapping version requests and retries.
- Display a localized reconnect message and button when disconnected, or a version-refresh retry when another request failed.
- Treat empty PICS branch results as a retryable condition, rather than a silent empty version picker.
- Preserve downloaded/game files, Steam credentials, existing branch list and selected platform; never print raw exception messages in UI. Errors are logged to AppLogger.
- Retain the existing authenticated login gate. No guest Steam access is introduced.

## Source and safety

Pinned to `master` commit `ac318d2d5e08b8e69c1ed8c253af005a8f3b329f`. The installer requires a clean tree and verifies exact Git blob hashes for all four modified files. Changes are planned fully in memory before writes; installer backups are restored on any failure. It never changes `master` protection, signing workflow, signing policy, keystores, passwords, Steam session store, app data, or Stardew saves.

Offline regression tests are structural/source-contract tests only; they do **not** prove Android compilation, Steam service connectivity, or real-device behavior. Use the repository's GitHub Actions Android build and then test a signed candidate on the device.

## Acceptance checks on test phone

1. With Steam connected, Download > Version shows `public` or other valid game branches.
2. Disconnect network and reopen Download: user sees Steam-disconnected message and Retry; the Download button stays disabled. Do **not** try to download or modify saves while offline.
3. Restore network and tap **Reconnect Steam & Retry**: wait for saved-session login and version refresh.
4. If saved session is expired, navigate to Settings > logout and log in again. Retry must not prompt for or log the Steam password itself.
5. Confirm unrelated Settings, Shizuku, and local save/mod functions still work.

The patch deliberately does not change underlying Steam transport or account authentication. A recurring `No network available` warning even when internet works requires separate connectivity investigation.
