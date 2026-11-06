# M25-03 R2E — Fail-closed game monitoring and device qualification hooks

Source: PR #60 `feature/m25-03-r2-journaled-bulk`, exact parent `293b23b9fb392fdbd0ee403ea538349b06043628`.

## Fixed in this one consolidated overlay

- AutoSync's earlier GameProcessMonitor treated a root-command error as "stopped" and could call onGameStopped / auto-push during an unknown game state. Now it uses the existing bounded GameSessionProbe, an explicit UNKNOWN state, and an 8-fixture pure Kotlin transition policy. A stop candidate needs a definite RUNNING, two successive NOT_OBSERVED samples, and a fresh recheck 3 seconds later. A command failure cannot trigger a stop event.
- The conservative `isGameRunning` compatibility Boolean remains `true` for UNKNOWN; the new `gameSessionStatus` StateFlow exposes the three-state result without pretending the Boolean is authoritative.
- The Shizuku-first manual status check in the Mods preview stays as shipped in R2D-S1, unchanged; neither Shizuku nor root is a live Mods write permit.
- Adds 3 no-write Android instrumented probes: an emulator-safe policy-only test, a Shizuku-specific on-device read, and an optional root-specific on-device read. Observations emit fixed, sanitized receipt tokens only; absence or denial is INCONCLUSIVE, not a PASS.
- Adds a **separate opt-in** zsh physical-device harness. It requires `--ack-read-only --serial <serial>`; root is checked only when `--probe-root` is requested. No uninstall, install, file modification, app force-stop, game process start/stop, or account/network access. It requires a matching APK pair to be installed separately; the harness does not independently attest the installed source identity.
- Hosted GitHub Actions source gate, pure JVM regression tests, debug APK pair artifact with exact Git SHA and SHA-256 list, and API36 policy-only emulator acceptance. No Gradle on Termux.

## Acceptance sequence

1. Apply one consolidated Devtool overlay and push to PR #60; hosted Actions must all pass. Do not merge before R2E CI.
2. Obtain the `R2E_APP_TEST_APKS` artifact from the exact successful R2E GitHub Actions run. The APKs are debug, not a release, and must not be treated as proof of physical-device qualification. Installation on a physical device requires separate explicit consent.
3. If a matching APK pair is **already installed**, run the read-only harness as `zsh scripts/devtool/m25_r2e_device_acceptance.zsh --serial localhost:5555 --ack-read-only`. It will call only the Shizuku read-only diagnostic; `--probe-root` additionally requests a root-process observation. Review the sanitized JSON.
4. Device observations remain provisional if Shizuku permission/service is absent, root is denied, or exact installed APK identities have not been independently proven. No real game mods writes are authorized.

## Remaining for production writes

Process absence is not a game-idle lock. Enabling actual bulk operations still requires a trustworthy exclusion against game start during the transaction, tested durable recovery across app process death/power loss, and independent source-and-installed-device evidence. `GameSessionSafety.permitsLiveBulkWrite(...)` remains hardcoded `false`, and Mod Manager's bulk preview has no Apply control. Physical device and release qualification remain false.
