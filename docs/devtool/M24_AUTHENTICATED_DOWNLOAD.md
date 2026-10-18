# M24 — Steam selection, recovery identity and local hash safety (source phase)

**Base:** postmerge M23 `master` `66b491e553db1adb27ad7be89049d462560b0ca3` / CI `39089587138` SUCCESS.

## Implemented (source-bound; not live qualified)

- Existing Cinderbox is the main game app. M24 downloads remain opt-in to a **separate empty directory** using M23 protection; no automatic transfer to the imported Cinderbox game, saves, mods or SMAPI.
- UI requires live Steam login, fresh PICS branch with positive build ID, enabled verification, an independent destination and a required explicit positive size estimate plus storage budget and write preflight. Storage estimates are *not* Steam depot sizes and do not guarantee sufficient space. Stale UI branch metadata **alone cannot authorize the service**.
- App-private interrupted download checkpoint now can bind its owned session to a positive PICS branch build ID. The binding is committed atomically and checked before resume and in the foreground service. Old M6/M14–M23 fixture methods still work, but unbound/legacy checkpoints cannot authorize an M24 service transfer. Interruption keeps partial bytes, never auto-deletes them.
- Service rechecks current live Steam session + PICS branch build before starting and after DepotDownloader completion. Branch drift, missing PICS metadata, lost login and failed SDK callbacks block local completion; the checkpoint remains for inspection. A nonempty license list is **not proof of Stardew ownership**; actual depot authorization is a server-side step, not established by this source gate.
- Local SHA-256 file consistency scan is compulsory before clearing recovery. The success screen explicitly says **LOCAL_SHA256_ONLY_MANIFEST_UNATTESTED**, not authenticated Steam depot manifest. No account IDs, passwords or tokens are recorded in new checkpoint metadata or CI reports.
- `m24-check` and `m24-full` wrapper shortcuts reuse existing Devtool DAG jobs, and both GitHub Actions workflows produce per-commit source-bound JSON. The Android test APK gets four *new*, app-private synthetic cases; no earlier M14–M23 device suites are replayed.

## Critical open gates

**M24 is not fully qualified.** Live licensed Steam depot ownership; authenticated per-depot manifest/chunk proof; a trusted depot manifest-to-files comparison; atomic game directory commit; real network interruption/cancellation/reconnection; storage revocation/shortage and consented real download are **NOT_RUN**, and source or synthetic test PASS cannot substitute for them. `verifyAndRecord` only records self-computed local hashes. The existing downloader writes in place to its owned separate destination and is not an atomic game-directory transaction; do not claim it is.

The previous M23 10/10 and 3/3 Android receipts retain their original source attribution. The new M24 synthetic lane must be run using exact matching CI APK and test APK; its runner deliberately reports `installed_source_verified=false` until separately attested. Publishing and release signing remain disabled.
