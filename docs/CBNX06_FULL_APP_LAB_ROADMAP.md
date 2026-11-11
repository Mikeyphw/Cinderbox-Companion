# Full CB-NX roadmap — accomplished, blocked, remaining

This is a continuation and consolidation of the prior roadmap, not a claim that later real-device milestones passed.

## CB-NX01 — Exact file browser / NXM handoff (implemented, hosted tested)

- Select exact Nexus mod ID and file ID; strict NXM identity and expiry parsing; browser-based legitimate Nexus authorization; native Android handoff/intent processing; no arbitrary first-file substitution.
- Preserve traditional browser download path, other supported managers, and graceful fallback. Source and hosted contracts green. Real browser/provider acknowledgment still not physically proven.

## CB-NX02 / CB-NX02B — Native downloads + UX and per-job queue controls (implemented, hosted tested)

- Native visible Downloads queue, progress, explicit review/approval, pause/resume/cancel/reorder/retry; approvals setting off by default; one exact file per intent; preserve state across process restarts and refuse stale URLs/duplicate admission.
- App-private archive staging and review, job ID linked to mod/file ID and receipt hash; bounded ZIP and safe install policy. Hosted device/emulator contracts green. Real personal-game install not approved.

## CB-NX03 / CB-NX03B — Pairing, bridge, exact-file inbox, privacy (implemented, hosted tested)

- Loopback-only Cinderbox bridge; local opt-in, nine-digit code, replay/nonce handling, lockouts, bearer token revocation; app-private, bounded, credential-free exact-file requests. Bridge cannot start downloads/installs by itself; only local Android UI action may move a request.
- Firefox uses memory-only token; no host-page pairing or token disclosure. Keep security negative suites. Hosted API36 synthetic pairing green.

## CB-NX04 / CB-NX04B/C — Canonical native authority + SMAPI evidence (implemented, hosted tested)

- Native journal + receipt proof as authority for transfer/review; stale/unavailable SMAPI evidence remains unknown; never assert exact installed-file or newer-file state without independent source proof; migration away from misleading badges. Hosted source/device contracts green.

## CB-NX05 / CB-NX05B/C — Page-level evidence UX, privacy, consent (implemented, hosted tested)

- Optional on-Nexus local read-only badge, consent default off, cached/stale states, redaction; not a provider-backed exact-file update claim; revoke invalidates in-flight replies. Firefox HF02/03 negative tests and HF04 inventory sync; targeted + Validate green on PR #2 HEAD `691fbf4...`.

## CB-NX06 — Physical Android 16 + Firefox/Iceraven acceptance (PARTIAL, actively blocked)

- Source-signed debug APK and `SOURCE_ATTESTATION.json` from CI: green, `42951853100`, Android PR SHA `c97ec1c...`.
- Real physical ARM64 API36 read-only preflight: PASS; Iceraven present.
- **BLOCKER** installed APK is a differently signed/different DEX build; exact CI-APK identity gate properly REFUSED. Cannot count physical E2E as passed. See `VERIFIED_STATE.md`.
- Proposed **CB-NX06-LAB** isolated, side-by-side app and Firefox lab configuration as next implementation. This is NOT implemented yet. Ensure production data immutability, separate app and port and identity, exact-source lab APK, and realistic browser tests.
- Outstanding physical checks: user-authenticated live Nexus file selection; actual Iceraven extension install and explicit opt-in, local pairing, status/revocation/fallback; exact-file review archive and unchanged production Mods; controlled lab-only install and rollback; all manual evidence.

## CB-NX07 — Final UX parity, packaging and release-candidate evidence (NOT STARTED)

1. Reconcile real lab and, if available, original production-intent physical evidence, noting limits. Include device build/OS/browser/extension and APK provenance with hashes; distinguish signed provider identity vs local journal.
2. Browser/Android UX parity: accessible pairing and consent, visible download queue and prompts, clear errors/retry, status badges with honest unknown/stale semantics, accessibility and visual screenshots, human review, no debug leaks.
3. Test complete permission/Origin/Host restrictions, request replay, exact-file provenance, stale/expired sessions, process interruption, duplicate jobs, review and rollback, backup/restore on disposable test Mods only; protect personal game.
4. Deterministic extension and Android artifact inventories, full hosted workflows and reproducibility receipts; installed signer/build provenance explicitly assessed. If required, obtain independent provider file authority; don't infer it from hash or installed mod name.
5. Final privacy review (never ship tokens, cookies, raw NXM URLs, personally identifying paths or logs), threat model, test evidence redaction, stakeholder/user approval of final review UX.
6. Manual release decision after all required physical acceptance. No merge, release signing, publication or claiming full qualification without explicit authorization.

## Scope not to accidentally expand

Do not silently change existing Cinderbox game location, add debug-only production bypasses, alter production signing, replace the user's installed Cinderbox, require live polling, or remove browser standalone/other-manager options. Implement lab safety before any live install tests.

## 2026-11-11 follow-up — user selected full Cinderbox debug variant

The isolated standalone mini-harness is superseded by a full Cinderbox UI variant (`:app:assembleCbnxLab`, package `com.sdvsync.cbnx06lab`). LAB02A implements source-level storage redirection, manifest isolation, separate opt-in loopback port 38472 and exact-source hosted artifact gate. **This is a build candidate, not physical qualification**; hosted Gradle and merged-manifest verification must succeed before manual installation. No real Nexus/Firefox pairing is automatic and no production data may be touched.

Next discrete gates:

- **LAB02B:** audit *all* transitive mutation and credential paths, including SAF and Steam fallback; add malicious-path/symlink/JNI negative coverage, merged-manifest physical read-only tests; block any unclassified real root.
- **LAB02C:** separately identity-scoped Firefox/Iceraven lab extension (new Gecko ID and storage namespace), different loopback 38472, explicit opt-in; XPI inventory/permission/source attest and real browser manual installation evidence.
- **LAB03:** lab-only exact mod/file handoff, visible native review, app-private staging hash and journal witness; real Mods and production APK hash unchanged before/after.
- **LAB04:** synthetic lab Mods ZIP traversal/replay/TOCTOU/stale token/cancel/pause/restart and rollback negative matrix on lab root; require independently reviewed receipts, never personal game data.
- **LAB05:** physical Android 16/ARM64 + real Iceraven read-only and active test receipts, exact installed lab APK bytes and signer vs hosted artifact, original app baseline unchanged, no data leakage.
- **CB-NX07:** accessibility parity, UI screenshots/manual review, release-source audits, full negative matrix, extension + APK reproducibility and privacy; release decision still requires explicit independent approval. No auto-merge or release signing.
