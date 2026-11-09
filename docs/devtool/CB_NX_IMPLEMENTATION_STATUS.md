# CB-NX01 — exact selected Nexus file handoff

Implementation candidate, not a qualified production release.

1. Native approved mod details retains `Download for review` and adds
   explicit `Browser + NXM` per file; each browser link has the exact mod/file ID
   and a fresh request identifier. API premium/free fallback uses that same file
   and prefers Firefox for its extension-capable browser handoff.
2. Firefox extension validates target IDs, selects an exact per-file manager
   action, checks returned NXM identity, and attempts handoff through Android.
   An on-page **Open in Cinderbox** anchor is available for manual OS prompts.
3. `NxmUriPolicy` checks game, path, ID, key, expiry, bounds and duplicate
   parameters before network activity. Concurrent native starts are blocked;
   failure logging does not contain unredacted NXM URLs.
4. The existing `ModDownloadService` stages the archive in `ModReviewQueue`.
   No auto-install or new protected filesytem writes are added.

Unit tests, JS contracts, source gates and GitHub Actions emulator jobs are
provided. They must actually run on GitHub. A logged-in Nexus free-account
session on Android Firefox plus physical Cinderbox receipt remains REQUIRED
before CB-NX01 can be declared complete. CB-NX02 through CB-NX06 remain planned.
