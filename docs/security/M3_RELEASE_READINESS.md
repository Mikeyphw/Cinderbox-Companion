# M3 — Android CI provenance and release qualification boundary

Status: **debug build evidence implemented; release SIGNING BLOCKED**.

The security branch's pre-existing Devtool Actions workflow stays `debug` + `apk` only. CI checks the source policy, runs the M0–M2 source contract, JVM tests, Android Lint, and builds a debug APK. The new `scripts/devtool/m3_build_evidence.py` records:

- the exact GitHub repository, ref, source commit and Actions run ID;
- the APK's SHA-256 and byte size;
- a verified Android debug signing certificate SHA-256;
- Android application ID, versionCode and versionName;
- explicit `qualified_release=false`, `publication_allowed=false`, `device_qualified=false` and `reproducibility_proven=false` flags.

The JSON file is **self-reported CI evidence**, *not* a signed provenance statement, not an independently reproducible build, and not proof that the inspected commit is trusted. Devtool must independently verify the workflow run identity, artifact ZIP hash, successful run status and APK signing identity during `actions android collect`. The JSON fingerprint is useful for diagnosing why debug builds from different CI runners are not in-place upgradable.

## Release-signing policy

`docs/security/M3_RELEASE_POLICY.json` intentionally disables publication and release signing. `python3 scripts/devtool/m3_build_evidence.py release` **fails closed**. This is not an accidental missing-secret fallback: CI never reads signing passwords or keystores. Do **not** put a keystore, passphrase, personal token or Steam credentials in this repository, workflow output or Actions artifact.

For a future production release, independently implement all of these in a separately reviewed change:

1. Create and back up a stable production signing key **off GitHub**; securely manage its recovery materials. Choose your permanent application ID and migration strategy before distributing the first production APK.
2. Configure a protected signing provider or secrets-based signing lane with least-privilege GitHub permissions, pinned source/tag, reviewed approval gates and zero secret logging.
3. Pin the expected **public** production signing certificate SHA-256 in reviewed policy. Reject unexpected certificates. Ensure the release APK updates with the exact same certificate and package name.
4. Verify the APK locally with Devtool's Android release/signature gates and test update-from-prior-version, downgrade refusal, backup/restore and rollback on real devices.
5. Produce a trusted provenance attestation with independently checkable run identity; prove reproducibility separately if it is claimed. Only then change the release gate and enable publishing.

At this phase there is **no release APK, no production signing, and no unattended app installation**.

## Validate M3 without Android SDK

```sh
python3 scripts/devtool/m3_build_evidence.py source
python3 -m unittest discover -s scripts/devtool -p 'test_m3_*.py' -v
# Must exit NONZERO while signing/device gates remain unresolved:
python3 scripts/devtool/m3_build_evidence.py release
```

The debug-only Actions workflows upload `M3_PROVENANCE.json` beside the APK. To independently cross-check a downloaded CI artifact (after comparing the SHA to Devtool's trusted run response):

```sh
python3 scripts/devtool/m3_build_evidence.py verify \
  --apk ./debug.apk --evidence ./M3_PROVENANCE.json \
  --source-sha "$(git rev-parse HEAD)"
```

Requires Android `apksigner` and `aapt`/`aapt2` for package verification. The provenance JSON and APK must be from the **same** Actions artifact. Never trust a provided source SHA without confirming it against GitHub/Devtool run evidence.
