# NEX-R2C — provider-backed schema verification

This milestone aligns Cinderbox's GraphQL browse selection with the nesting shown in Nexus Mods' own public GraphQL client (`modCategory { name }`, `updatedAt`) and maps the returned ISO timestamp and category into the native cards. It is **not a live provider capture** unless the opt-in credentialed workflow actually completes.

## Evidence levels

- Ordinary PR workflows: Python source-gate + fully **synthetic** negative fixtures and hosted JVM unit tests. **Not qualified** as live Nexus validation, device navigation, install/download safety or publication.
- Explicit manual workflow dispatch: source-bound, authenticated, read-only request to `https://api.nexusmods.com/v2/graphql`, followed by REST v1 mod detail and file metadata for the first returned mod. No website scraping, WebView, file download, login mutation, mod tracking or endorsement.
- The manual lane cannot run without the repository Actions secret `CINDERBOX_NEXUS_API_KEY`. The key must be the user's own Nexus API key, not a token created for another application. It is injected only into the workflow environment and never accepted as a CLI argument.
- `workflow_dispatch` should be used only on the intended branch after the workflow is available on the default branch. The live lane is not automatically invoked on pull requests and **must not be mistaken for a green PR check**.

The probe extracts the actual bundled GraphQL document from `NexusCatalogOperation.kt`. It tests the Stardew game-ID 1303 filter, nested category and timestamp selection, provider total/first-page shape, a second offset page when one full page is returned and more records exist, the REST detail ID, and REST file-list envelope. It fails closed on unknown schema or access failures. It does not establish complete category taxonomy, actual user-specific Nexus sign-in, native Discover→detail→file-review navigation, or compatibility with a physical Android device.

The only emitted success artifact is a minimal Boolean/status receipt. No raw responses, account names, API tokens, mod names, mod IDs, file paths, links, quotas, personal files, or installation records are recorded. Errors are stable codes, with no provider exception data or headers.

Official references:
- https://github.com/Nexus-Mods/discord-bot/blob/master/src/api/queries/v2-mods.ts
- https://github.com/Nexus-Mods/node-nexus-api

Release, publication, live update, Shizuku/root, filesystem writes and automatic download/install gates remain unchanged and disabled where previously disabled.
