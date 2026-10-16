# M16 — stable debug signing, never release signing

**Goal:** eliminate per-GitHub-run Android debug-certificate rotation for `com.sdvsync`.
Both the standard PR/push CI workflow and Devtool Actions' debug APK workflow use
one persistent PKCS12 key uploaded to GitHub Actions secrets. Android instrumentation
APKs are signed with the same pinned debug key. No key or password is committed.

## One-time setup (Termux, JDK keytool, OpenSSL, `gh` authenticated)

```sh
cd "$HOME/Code/Cinderbox-Companion"
python3 scripts/devtool/m16_debug_signing.py setup --upload
```

The command generates `~/.local/share/cinderbox/debug-signing/cinderbox-debug.p12`
and its `password` once (owner-only permissions), reuses them on subsequent runs,
then uses `gh secret set` via stdin. It uploads repository Action secrets:
`CINDERBOX_DEBUG_KEYSTORE_B64`, `CINDERBOX_DEBUG_STORE_PASSWORD`,
`CINDERBOX_DEBUG_KEY_PASSWORD`. It sets public GitHub Actions repository variable
`CINDERBOX_DEBUG_CERT_SHA256` to the certificate fingerprint. Do not post, commit,
archive with source, or share the local keystore or password. Back up **both** securely.
Without those secrets and the pin, CI APK generation fails before the build. A PR
from another repository is rejected; fork PRs do not receive these secrets.

## Bound verification

- CI first runs offline regressions (`test_m16_*.py`), then provisions the PKCS12
  outside the checkout under `$RUNNER_TEMP` with mode `0600`.
- The Gradle `debug` build type uses `ciDebug` **only** when CI sets
  `CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING=true`; missing keystore/passwords
  trigger an exception, not fallback. Unqualified local builds may still use
  Android's ordinary per-machine debug certificate.
- The assembled app APK and AndroidTest APK each pass `apksigner verify`, the
  existing APK signing-block certificate parser, debug-subject verification,
  and a SHA-256 certificate comparison with the public pinned variable.
- M3 provenance continues recording APK SHA-256 and signing certificate. M13
  debug qualification and production release gates remain unchanged.
- The signed-candidate release workflow continues using **separate** credentials
  and is not modified. M16 does not publish, install, uninstall or clear data.

## Migration / update continuity

The **first** M16-signed APK will use a new certificate, different from previously
installed M15 debug APKs. One final clean uninstall/reinstall may be necessary.
After that, builds using the **same preserved M16 keystore and passwords** can use
`pm install -r` (or the M15 `--allow-replace` option). Still perform normal APK
provenance checks; APK signing does not authorize device or release qualification.

**Do not regenerate the key if a key already exists.** If the key or password is
lost, recovering continuity is impossible with ordinary in-place installation;
restoring the original keystore backup is preferable to wiping app data.

## Verification without device changes

```sh
python3 scripts/devtool/m16_debug_signing.py source
python3 -m unittest discover -s scripts/devtool -p 'test_m16_*.py' -v
```

In GitHub, verify the green `M16 verify pinned application APK signer` and
`M16 verify pinned instrumentation APK signer` steps in both debug workflows.
Do not treat past M14 8/8 or M15 6/6 device results as rerun or production-pass.
