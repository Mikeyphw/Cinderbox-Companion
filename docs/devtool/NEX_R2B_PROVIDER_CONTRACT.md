# NEX-R2B — Nexus provider response integrity (candidate)

## Scope and provenance

This milestone strengthens the existing Nexus v1 REST mod/details/files mapping and
v2 GraphQL browse results. It **does not claim live authenticated Nexus schema
qualification**. The two JSON files under `scripts/devtool/fixtures/nex_r2b/`
are **synthetic schema-shaped fixtures, not live provider captures**. They
contain no Nexus keys, session tokens, user identifiers, account information,
or scraped pages. They should never be presented as evidence of live API success.

Mappings follow documented Nexus REST v1 patterns (`mod_id`, `files`, `file_id`,
`category_name`, `is_primary`, `uploaded_timestamp`) and the preexisting NEX-R1
GraphQL operation (`modId`, `totalCount`, `nodes`, `offset`). The exact live
GraphQL schema/operators, live taxonomy, authenticated category/tag filters,
and a real Discover→detail→file-review path remain **unqualified**.

## Provider boundary invariants

- No missing, null, zero, fractional or invalid mod/file identifiers become a
  usable route or file action; malformed results are omitted or refused.
- `totalCount` must be a nonnegative JSON integer. The client may not silently
  convert missing/invalid values to `0` (a false empty catalog).
- `hasMore` uses the raw provider node count and requested server offset.
  Filtering out invalid display nodes must not fabricate an end-of-catalog.
- Missing file `category_name` is `UNSPECIFIED` unless `is_primary` is explicitly
  true; no unknown file is misrepresented as Main.
- Provider Unix seconds are converted to milliseconds only in a bounded,
  plausible date range. Missing/invalid dates remain unavailable.
- This milestone adds no provider credentials, network endpoints, write
  permissions, WebView, privileged device actions, or download capability.

## Acceptance

The new hosted job runs source/negative fixtures and pure JVM mapping tests.
Existing app-wide CI still owns Debug APK and Android instrumentation; NEX-R2B
intentionally does **not** dispatch a second redundant emulator job. Hosted
screenshots remain candidates rather than approved goldens.

Follow-on live provider qualification requires an explicit, secure end-to-end
plan using the user's own Nexus API credentials on their device (not CI logs).
No credential is shipped in the repository, fixtures or build artifacts.
