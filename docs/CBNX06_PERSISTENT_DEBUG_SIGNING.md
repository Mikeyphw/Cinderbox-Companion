# CB-NX06: persistent CI debug signing (production package, no install)

The CB-NX06 hosted `assembleDebug` job uses Android's `ciDebug` PKCS#12
configuration. It refuses to publish if any signing secret is absent, if the
keystore alias is not `androiddebugkey`, or if the resulting v2 APK signer
certificate does not equal the signer observed on the installed Cinderbox.
It does **not** use the release signing configuration, a new local debug key,
or any fallback signing identity.

## Provisioning (one-time, by repository owner)

Store the following GitHub Actions **repository secrets** under
`Mikeyphw/Cinderbox-Companion` → Settings → Secrets and variables → Actions:

- `CINDERBOX_DEBUG_KEYSTORE_BASE64`: base64 of the **existing** PKCS#12
  private-key keystore containing alias `androiddebugkey`, with the signing
  certificate matching the installed application.
- `CINDERBOX_DEBUG_STORE_PASSWORD`: that PKCS#12 keystore password.
- `CINDERBOX_DEBUG_KEY_PASSWORD`: password for `androiddebugkey` (often same as
  the PKCS#12 store password).

The full expected certificate SHA-256 is:
`48954c3e9d4f9f2acaab60d56b43f06a9b7d3e3f27df3e9c2f2f9f9e6261db16`.

**Do not generate a new keystore** or copy a release private key into GitHub
Secrets to satisfy the test. If no legitimate persistent debug keystore has
that certificate, the build should refuse and the existing installation must
remain untouched. Do not commit the key, keystore, base64 text, or passwords.

## Build and evidence

On the existing PR #89, the workflow checks the exact PR head, runs the
existing source and negative tests plus signer-policy negatives, loads the
keystore only into the hosted runner's temporary directory, validates its
certificate with `keytool`, and builds with mandatory
`CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING=true`. A second independent
`apksigner verify` check requires **one** v2 signer with the same certificate.
Only after that check succeeds will GitHub upload
`cbnx06-exact-source-debug-apk`, containing `app-debug.apk`, `SHA256SUMS`,
`SOURCE_ATTESTATION.json`, and `SIGNER_ATTESTATION.json`.

**Signer match is not byte match.** The existing physical-acceptance harness
continues to refuse if the installed APK bytes differ from the CI artifact.
No physical Nexus, install, rollback, or release qualification is implied.
Because this is still package `com.sdvsync`, do not install the debug APK on
production merely to unblock testing; the separate isolated lab remains the
next safe physical testing path.

Security note: Actions secrets are exposed to the signed-build job on trusted
same-repository PRs. Restrict who can push to the feature branch and do not
make this a `pull_request_target` workflow. Fork PRs have no secrets and are
expected to refuse. Use an environment with required reviewers if stronger
signing-secret protection is required.
