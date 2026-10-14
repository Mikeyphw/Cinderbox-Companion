# M3G – Steam reliability and diagnostics

Source pinned to `master` at `8e718e72eb8da0dc30f8827a2f20a52e240c5011`.

## Verified device issues behind this work

- JavaSteam 1.8.0 `HardwareUtils.getMachineID()` executes desktop `dmidecode`/`lshal`; rooted-device `strace` established the exact fallback and Android's `/system/bin/lshal` crashes with SIGSEGV. M3G rewrites this vendor method *at build-time* using AGP ASM `InstrumentationScope.ALL` to return a persisted, per-install machine ID, with a fail-closed check on vendor ABI changes. No root/system binary modifications. Note: machine ID necessarily changes once, and Steam Guard might require reapproval after upgrade.
- Android network capability check spuriously rejects saved-session recovery despite functioning Wi-Fi. M3G records the capability failure but lets real Steam transport provide the authoritative connection result.
- Unexpected Steam WebSocket drop after 10–30 seconds. M3G records explicit close/timeout/send/stream events and raises 5s Ktor ping interval to 20s. It cannot promise to eliminate every server/network disconnection; device evidence must confirm impact.
- Single-shot automatic recovery after unexpected disconnect: M3G introduces six capped attempts with increasing delays (2,4,8,16,30,30 seconds) and retains manual Retry. No infinite loop.
- No published GitHub Releases is informational, not a Cinderbox update failure; lower misleading ERROR logging.
- Download tab initially reports offline while manual Retry reconnects: improved auto recovery and global status visibility; PICS access checks remain bound to actual logged-in Steam state.

## UI and evidence

- Compact live Steam indicator in all top bars; tap for transport status/network snapshot and manual Retry while offline.
- Hidden developer diagnostics unlocked by tapping Settings → About version seven times. Works from prelogin or signed-in Settings.
- One-hour, one-minute-bucket connection history graph (color-coded), bounded 180-event token-free history persisted in private preferences across launches.
- Unexpected disconnect and failed network capability snapshots include current transport category and INTERNET/VALIDATED boolean flags; no SSIDs, URLs, hostnames, accounts, tokens or Guard codes.
- Export sanitized JSON via Android Storage Access Framework; no privileged paths or broad filesystem writes.

## Not within scope

- No real game save, mod, backup, cloud sync, installation, signing, publishing, or permissions changes.
- No claim that this fixes every Steam WebSocket drop. The point of M3G diagnostics is to make unaccounted disconnects observable.
- Do not silently publish or auto-install signed candidates.

## Validation to perform after applying

1. `python3 -m unittest discover -s scripts/devtool -p test_m3g_steam_reliability.py -v`
2. On GitHub Actions run `:app:testDebugUnitTest :app:lintDebug :app:assembleDebug` before merging.
3. On Android install a compatible-signed candidate through the established safe workflow; verify `strace -f -e execve -p $(pidof com.sdvsync)` never shows `dmidecode` or `lshal` at login.
4. Keep Cinderbox in foreground on Wi-Fi for 10 minutes; capture connection changes and export JSON. Confirm automatic retry and no permanent spinner.
5. Verify badge, 7-tap unlock, history, export, reboot/reopen history persistence, branch selection, Settings and Shizuku unaffected.
6. Check SHA/certificate compatibility before in-place install. Never uninstall or clear data just to test.

## Known build qualification limit

This ZIP was generated without a complete Android SDK and dependency graph in the authoring container. Static source-contract checks and transactional installer checks are **not** a substitute for the Android Gradle build. Treat M3G as a candidate until CI passes; do not merge on source tests alone.

M3G FIX1: Corrected reconnect anchor to match source at pinned master (12-space indentation);
source transformations are staged until all anchors validate. The failed pre-fix installer rolled back.
