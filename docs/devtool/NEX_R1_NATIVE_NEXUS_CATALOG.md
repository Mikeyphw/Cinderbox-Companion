# NEX-R1 — Native Nexus Mods server-side catalog

Status: **candidate**, not hosted-qualified until PR checks and actual screenshot artifacts pass.

## Scope

- API-only. No WebView, ChromeXt, userscript loading or browser permissions.
- Retains the previously tested search operation for other callers and legacy regressions.
- New typed `NexusCatalogFilters` + bound GraphQL variables: Stardew Valley ID 1303,
  exact category name, included/excluded tags, updated-within periods, minimum downloads,
  minimum endorsements, provider sort and paginated full-catalog browsing.
- Refine modal uses draft inputs and Apply; previously selected filters survive page loads.
- Installed/Saved are clearly marked as **local-only** filters. The UI shows provider
  total only when no local-only filter is selected. Category suggestions are explicitly
  *suggestions from loaded cards*, not a complete Nexus category directory.
- Every change cancels stale requests; pagination preserves current server filters.
- No Nexus key means a read-only error/prompt, never fake results or hidden scraping.
- Existing mod-download approvals, Steam login, storage, SMAPI, root/Shizuku, automatic
  updates, release qualification and privacy gates are unchanged.

## Qualification

- Source gate validates old security policy, new GraphQL variables, UI tags and stale-request gate.
- `:app:testDebugUnitTest` tests bound values, combined filter logic, date thresholds and pagination.
- Hosted GitHub API36 instrumentation screenshots: Mods + filter modal at 360 and 393dp,
  default font; no real login, account data or device writes.
- Neither screenshot evidence nor Android emulator tests prove Nexus credentials, API
  acceptance, network-dependent content, native-golden pixel parity, or real-phone acceptance.
- Live API schema and every query sort/filter must still receive authorized integration
  acceptance against Nexus before this feature is called production-qualified.

## GraphQL schema provenance

Nexus-Mods official Discord-bot `IModsFilter` and `IModsSort` types include gameId,
categoryName, tag, updatedAt, downloads, endorsements and createdAt. Their `mods`
operation uses `ModsFilter`, `[ModsSort!]` and paginated results. This is source-based
schema qualification; a live Nexus API call has **not** been performed with a user key.

## Next

NEX-R2 enriches cards and mod detail only after the server filter flow is green.
No external browser integration is required for NEX-R1 or NEX-R2.
