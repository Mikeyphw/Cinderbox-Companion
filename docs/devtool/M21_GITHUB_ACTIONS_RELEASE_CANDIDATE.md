# M21 GitHub Actions — protected manual release-candidate build

This is an additive standalone manual workflow, **not** a conversion of the M3/M16 debug workflows to release builds. It deliberately does **not** change M21 PR #26 HEAD (`d93d21d2f569d947bce91099ef112e3b6a793452`) or rerun its U/I/T device tests (14/14 passing). Prior M14–M20 74 tests are also preserved.

## Why a separate PR against `master`?

GitHub Actions normally requires a `workflow_dispatch` workflow definition on the default branch. Merge this standalone workflow in a separate PR against `master` first, leaving PR #26's already-tested source unchanged. The manual workflow is dispatched on `master`, and checks out the **exact** reviewed M21 head `d93d21d2f569d947bce91099ef112e3b6a793452` to build the candidate. This is a one-off pinned candidate, not a generic compile-and-sign untrusted PR command. Updating its SHA requires review of a workflow change.

## Required GitHub Environment: `cinderbox-release`

Create the environment in GitHub repository Settings → Environments. Restrict permitted branches to `master`, and optionally require a human reviewer before signing. Repository must allow Actions secrets and environment access. Configure **environment secrets**, never commit or paste their values into chat, files, command history, Actions step output, PR logs, or artifacts:

- `CINDERBOX_RELEASE_KEYSTORE_B64`: base64 of existing `~/.config/cinderbox-signing/release.jks`, preserving the original key; the environment secret value is encrypted at rest by GitHub. The original keystore must be backed up separately.
- `CINDERBOX_RELEASE_STORE_PASSWORD`: current keystore password.
- `CINDERBOX_RELEASE_KEY_PASSWORD`: key password (same if the keystore is PKCS12 with unified password).

And two **environment variables** (public SHA-256 certificate fingerprints, no private material):

- `CINDERBOX_RELEASE_CERT_SHA256`: independently determined public certificate SHA-256 from `keytool` for alias **`cinderbox`** of the existing keystore.
- `CINDERBOX_DEBUG_CERT_SHA256`: *existing pinned M16 CI debug signer fingerprint*; it must be different from the release fingerprint. Copy the existing trusted repository variable into this restricted release environment; do not replace the repo debug pin.

If alias `cinderbox` is absent or belongs to the wrong signing identity, do **not** create a new alias: reconcile Gradle signing configuration first. The workflow validates this exact alias before building.

The workflow references environment-scoped variables/secrets only. The keystore is reconstructed in `$RUNNER_TEMP` using restrictive permissions and symlinked to `source/keystore.jks`. Only the explicitly reviewed code at the pinned SHA is built. Signing material is removed before artifact upload; no release/Play Store upload occurs.

## Upload the existing keystore to the environment securely (Termux)

The `gh secret set` command accepts the value from standard input. Do not run with shell tracing (`set -x`). Use the actual path, but never print or paste the resulting base64.

```sh
REPO=Mikeyphw/Cinderbox-Companion
ENV=cinderbox-release
KEY="$HOME/.config/cinderbox-signing/release.jks"
test -f "$KEY" || exit 1
base64 < "$KEY" | tr -d '\r\n' | gh secret set CINDERBOX_RELEASE_KEYSTORE_B64 -e "$ENV" -R "$REPO"
```

In GitHub Settings → Environments → `cinderbox-release`, set the two password secrets and two fingerprint variables. Do **not** set these credentials in repository-wide secrets; the release environment limits their exposure.

## Manual dispatch after the workflow PR is merged

```sh
gh workflow run cinderbox-release-candidate.yml \
  -R Mikeyphw/Cinderbox-Companion --ref master \
  -f reviewed_source_sha=d93d21d2f569d947bce91099ef112e3b6a793452
```

Inspect the run (do not assume success):

```sh
gh run list -R Mikeyphw/Cinderbox-Companion \
  --workflow cinderbox-release-candidate.yml --limit 3
```

On success, download the `m21-signed-release-candidate` artifact (`APK`, `SHA256SUMS`, `M21_RELEASE_CANDIDATE.json`). The candidate is not installed, released, or distributed automatically. Compare the downloaded APK's independently computed SHA-256 with `SHA256SUMS` and the receipt; verify certificate against the locally inspected keystore.

## Complete M21 release-security lane R

Keep PR #26 local checkout at `d93d21d2f569d947bce91099ef112e3b6a793452` and use the existing successful **debug CI** run `38946596038` when invoking `scripts/devtool/m21_campaign.py --release-audit`. Point `--release-apk` to the downloaded signed release candidate; supply actual independently verified APK/certificate/debug pins. Do not substitute the *new manual release workflow run ID* for `--run-id`: M21's audit still verifies the original source-bound debug/test APK provenance.

The outcome remains `release_qualified=false` and `publication_allowed=false` even when all four R checks pass. Publishing requires a separate authorized release decision. In particular, Android cannot normally update the currently debug-signed installed Companion app in place using a different release signing certificate; do not uninstall or clear the user's app.

## Persistent Devtool improvement record

**DEV-M21-REL-001 — Signed release candidate distinct from debug-oriented Devtool.** Existing `.devtool.toml` and `devtool-android-build.yml` intentionally support debug builds, so invoking a release variant through those would violate their source safety contracts. The resolution is a separate manual default-branch GitHub Actions workflow and independent signed-artifact verifier, preserving M16 source/CI gates and 14 completed M21 device tests. Status: **Implemented; release run pending**. This document is a standalone append-only campaign supplement to the cumulative `docs/devtool/DEVTOOL_IMPROVEMENTS.md`, to avoid a conflicting edit to that file while PR #26 is open.
