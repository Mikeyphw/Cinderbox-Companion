# NEX-R5 — Unified native mod details, safe formatted text, file actions and community browser fallback

## What changed

- Main approved dark `mod_detail` route now renders provider HTML/BBCode with the existing native `TextView`/`HtmlCompat` path instead of stripping markup and truncating the entire description at 6,000 text characters. The payload is bounded to 32,000 characters, executable blocks and image elements are removed, and all clickable spans are rebuilt through strict HTTPS URL validation. No WebView/browser engine is embedded.
- Existing grouped provider files and descriptions/changelogs appear on the first details screen with per-file **Download for review** actions. These invoke the existing `ModDetailViewModel.installFile()` and `ModDownloadManager` / `ModDownloadService` / `ModReviewQueue`; downloading an archive does **not** install it. The mandatory user review of proposed file changes remains unchanged.
- The legacy `mod_detail_advanced` compatibility route remains for previously qualified navigation and file operations, but its duplicated mod overview/description are removed: it is now a focused **Files & downloads** route.
- New **Media** and **Posts** sections provide correctly scoped browser actions, without fabricating comments or gallery images. The verified REST v1 mod details model returns only `picture_url`, and Cinderbox has no verified API contract binding individual legacy mod IDs to a gallery or Posts comment thread. Nexus's generic GraphQL comments/media queries are not sufficient evidence for a particular mod page. Browsing these sections opens the external browser using an exact, validated Nexus page URL, never a WebView.
- A new source gate, JVM URL-policy regression tests and Android 36 synthetic Compose fixtures check rich text/link sanitization, file action callbacks, media/posts navigation and six screenshots across 360dp and 393dp at 100% font. Actual hosted CI must pass before merge.

## Boundaries

- No Nexus credentials are embedded, mocked as live, or added to CI.
- No scraping, unofficial undocumented API calls, comment posting, user automation, Nexus paywall bypass, account bypass, silent install, new privileged filesystem writes, release approval, or automatic publication.
- Gallery/videos and per-mod Posts remain **browser fallback only** until an independently verified official mod-scoped API exists. This is not equivalent to native threaded posts or an in-app multi-image gallery. The UI says so plainly.
- Source/fixture tests are not physical-device, authenticated Nexus, release-signing or real download qualification.

## Acceptance

1. Python source/negative gates and all NEX R1–R4 source gates green.
2. Hosted JVM unit tests, Gradle compile, Android 36 instrumentation and actual PNG evidence green, both 360dp/393dp, 100% text.
3. One source-pinned Devtool overlay applied, canonical 13-path source map, exact staged diff, one commit, push and PR.
4. Keep branch unmerged until the hosted checks are all green. No local Gradle or real device use is required.

## Provenance

Pinned master commit: `33c6db1b30a3d3517f538a2ddb81073694f9ef69`.
Pinned master tree: `6ce56fba93b08dc53740483ed364e46cdd5b141d`.
Prior merged NEX-R4: PR #83.
API references: https://github.com/Nexus-Mods/node-nexus-api and https://graphql.nexusmods.com/ .


## HF02 state-machine audit

Downloading a selected file first requests a URL and then dispatches the
existing guarded download service. The user may not initiate a second URL request
while the first is pending. The request-in-flight UI flag resets on success,
error, and cancellation. `ModDownloadService` still stages the archive for explicit
review, never installs automatically. No new review privilege or release gate.


## NEX-R5 community capability probe (posts and additional media)

The **official** Nexus GraphQL v2 schema currently exposes `commentThread(commentThreadId)`
(without a documented mod-to-thread mapping) and site-wide `media(filter)` where
`MediaSearchFilter` has game/owner/type/text fields but **no mod ID field**.
These are not safe to treat as per-mod Posts/Gallery. Native user posts or images must
never be inferred from author, game, fuzzy search or a coincidental numeric ID.

The consolidated overlay includes a standard-library-only, **read-only** probe:

```sh
# No network; prove expected behavior from documented, synthetic schema fixtures.
python3 -B scripts/devtool/nex_r5_community_probe.py \
  --fixture scripts/devtool/fixtures/nex_r5_community/documented_v2_schema.json
python3 -B -m unittest discover -s scripts/devtool -p 'test_nex_r5_community_probe.py' -v

# Optional: bounded live schema introspection + mod identity (1303=Stardew Valley).
python3 -B scripts/devtool/nex_r5_community_probe.py --live --mod-id 7001 \
  --output "${TMPDIR:-/tmp}/nex-r5-probe-$(date +%s)-$$.json"  # Exclusive create, mode 0600.
```

For a live authenticated probe, configure `NEXUS_API_KEY` only in the local
shell environment; **do not paste keys in logs or arguments, commit receipts,
use real user content in fixtures, or put a secret into PR-triggered Actions**.
No key is needed to attempt anonymous schema introspection. The probe accesses
**only** `https://api.nexusmods.com/v2/graphql`, disables redirects, caps response
bytes/time, runs fixed queries (`__type` metadata plus optional mod identity),
and stores only a 0600 sanitized JSON receipt (never keys, comments, images or raw responses).
Transport/auth/graphql errors are recorded as `INCONCLUSIVE`, not "unsupported".

### Interpreting the receipt

- `NO_MOD_SCOPED_CONTRACT`: official live schema does not expose a trustworthy mod-scoped
  Posts/Media relationship. Continue native cover + **external Nexus tabs**.
- `CANDIDATES_UNVERIFIED`: a possible mod-specific relationship was found. **NOT** a
  release gate pass. A follow-up must validate mod/game identity, thread ownership,
  content attribution and pagination against a real authorized Nexus request.
- `INCONCLUSIVE`: network/auth/schema failure; rerun manually or investigate authorization.
- `native_qualified` remains `false` for ALL results. This probe intentionally never
  downloads user comments or media and never enables unqualified native UI.

The NEX-R5 GitHub Actions PR runs the offline fixtures and an **anonymous** live
schema probe, uploading only the sanitized receipt. A PR should not be marked as
having native posts/gallery merely because the probe job is green. The optional
live probe is observability, not a release acceptance criterion.

Reference: https://graphql.nexusmods.com/ (GraphQL v2, still evolving). Follow
https://help.nexusmods.com/article/114-api-acceptable-use-policy for API terms.
