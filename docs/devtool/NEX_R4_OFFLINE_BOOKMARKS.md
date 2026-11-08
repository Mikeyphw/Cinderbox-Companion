# NEX-R4 — Saved mod metadata stays useful without Nexus access

Scope: native Material3, 100% default font, no new browser view, no release changes.

The Saved chip already shows previously bookmarked metadata without a Nexus key, but
its card tapped the same remote detail route used by online catalog results.
NEX-R4 changes only that one no-key interaction: saved cards open an in-app
**metadata-only, offline** bottom sheet. A configured Nexus API key keeps the
original remote detail route. Offline cards do not request provider thumbnails.

The sheet shows bounded metadata already stored in `ux05_mod_bookmarks` and makes
no claims about live versions, game/SMAPI compatibility, files, downloads, or
installation. The existing Nexus access setup remains available via the CTA.
The existing bookmark removal action is unchanged. The stored bookmark data
is not a Nexus login token or authenticated account export.

## Acceptance and limits

- Hosted Android API 36 real MainActivity at 360dp and 393dp, default 100% font.
- Start with no Nexus key, inject a **synthetic local bookmark** before launch,
  open Mods → Saved → card → offline sheet → Close, and assert no provider calls.
- The CI emulator is isolated/offline and data-cleared per viewport; never run
  these destructive fixture operations on a physical device or user account.
- Saved images must not trigger remote image fetching in this no-key mode.
- Screenshots are authentic **hosted emulator** images of synthetic local data,
  not real Nexus results or approved visual goldens.
- Physical-device, real-Nexus-account, privileged file writes, download/install,
  Steam and release/publication acceptance remain separate and disabled.

This milestone builds on merged NEX-R1/R2/R3, and is intentionally narrower than
full offline caching of provider pages. It does not download mod archives.
