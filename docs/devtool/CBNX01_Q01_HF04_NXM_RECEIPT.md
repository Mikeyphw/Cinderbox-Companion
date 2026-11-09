# CB-NX01 Q01 HF04 — redacted NXM ingress receipt

This diagnostic changes **no** URI validation, download behavior, browser integration, or review queue. It adds Android `Log.i` records with fixed, non-sensitive event codes under tag `CBNX01_NXM_RX`. These records provide an observable answer when an invalid-link toast is invisible. There is no key, URL, expiration, mod name, or other user data in this log.

## Safe physical validation

Install the CI debug APK built from this commit. ADB serial: `localhost:5555`. Trigger this fake expired NXM URI (it must never authorize a download):

```zsh
adb -s localhost:5555 shell am start -W -n com.sdvsync/.MainActivity -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d 'nxm://stardewvalley/mods/50535/files/178239?key=diagnostic&expires=1'
adb -s localhost:5555 logcat -d -v brief -s CBNX01_NXM_RX:I '*:S' | tail -n 30
```

Expected: `NXM_RECEIVED_VIEW` and `NXM_PARSE_REJECTED`. If absent, the Android process did not reach `handleIncomingIntent` (or logs are unavailable). If present, Android delivered the URI and the parser rejected it, even if no toast appears. Do **not** print all logcat or paste real `nxm://` URLs; valid Nexus keys and expires are private.

For a real user-authorized Nexus handoff, compare the fixed event codes: `NXM_PARSE_ACCEPTED` means the URI reached Cinderbox; `NXM_URL_RESOLUTION_STARTED` means the app tried Nexus; `NXM_DOWNLOAD_MANAGER_REQUESTED` and `NXM_MANAGER_RETURNED_NOT_STAGED_PROOF` are **not** proof of a staged archive. `NXM_RESOLUTION_OR_DOWNLOAD_FAILURE` indicates a later error. Use the existing physical acceptance script for actual archive staging.

Until a matching CI APK runs on the physical Android 16 device, this is **source-only diagnostics**, not a device qualification.
