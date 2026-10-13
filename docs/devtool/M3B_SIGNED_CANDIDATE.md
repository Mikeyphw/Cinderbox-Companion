# M3B — signed candidate and device upgrade qualification

This introduces **opt-in** release-candidate signing. It does not enable
publication, auto-installation, or official release qualification. The existing
Devtool Actions debug workflow is unchanged and remains available without keys.

## Default is disabled

`docs/security/M3B_CANDIDATE_POLICY.json` deliberately starts with
`candidate_signing_enabled=false` and a null certificate. The new GitHub
workflow fails closed until reviewed changes are merged into `master` and the
policy is explicitly enabled with a pinned certificate fingerprint.

## Create a stable key (explicit user action)

Do not create the key inside your Git working tree. On a secure machine with
JDK 17+ and a **trusted** local terminal, run:

```sh
python3 scripts/devtool/m3b_key_setup.py create
python3 scripts/devtool/m3b_key_setup.py inspect
```

Key creation is interactive and refuses overwriting an existing keystore. It
uses the alias `cinderbox` and stores the PKCS12 keystore under
`~/.config/cinderbox-signing/release.jks` with restricted permissions. Keep
**multiple encrypted off-device backups** of the keystore and passwords:
losing this key may make future in-place Android updates impossible. This key
has never been configured automatically by this patch.

The `inspect` command displays the **public** signing-certificate SHA-256.
Remove `:` separators and lower-case the 64 hex characters. Commit that
fingerprint in `M3B_CANDIDATE_POLICY.json`, together with
`candidate_signing_enabled: true`, **only after source review**. Never commit
the keystore, passwords, or base64 encoding of it.

Configure these three **GitHub Actions environment secrets**, scoped to the
`release-signing` environment on the repository:

- `CINDERBOX_RELEASE_KEYSTORE_B64` — base64 of the PKCS12 keystore
- `CINDERBOX_RELEASE_STORE_PASSWORD` — keystore password
- `CINDERBOX_RELEASE_KEY_PASSWORD` — alias key password (often same as store)

Use GitHub's UI or an authenticated `gh secret set --env release-signing`
command. Never put secret values on a command line or in terminal history.
Protect the GitHub environment with required reviewers and restrict deployment
branches to `master`. Restrict `master` with protected-branch rules. Repository
administrators should review the workflow and any subsequent changes before
allowing release keys to be used. Secrets are materialized only during the
manual job, removed via a shell trap, and excluded from uploaded artifacts.

## Register/execute

GitHub must see the new workflow on the default branch (`master`) before
manual dispatch. Once reviewed, merge the **full M3B implementation** to
`master`; registering only the workflow without the policy and checks will
make it fail safely. The workflow explicitly rejects all refs except
`refs/heads/master` and requires confirmation string `SIGNED_CANDIDATE`.

Run via GitHub Actions → **Cinderbox Signed Candidate** → Run workflow
(default branch `master`). No app release is created and the candidate is
retained in an Actions artifact for 14 days.

The existing M3 policy in `M3_RELEASE_POLICY.json` stays release-blocked. M3B
adds a *separate*, explicitly configured signing lane but does not alter the
trusted Devtool Actions debug dispatch contract.

## Check upgrade compatibility before installing

On Termux with Android SDK Build Tools (`apksigner`, `aapt`/`aapt2`) and a
**specifically authorized ADB device**:

```sh
python3 scripts/devtool/m3b_upgrade_preflight.py \
  --serial YOUR_DEVICE_SERIAL --apk /path/to/candidate.apk
```

This only reads package metadata and copies the currently installed base APK
into a temporary local directory. It does **not install**, request root, delete
saves or run instrumentation. Mismatched signing certificates are blocked;
versionCode downgrades are blocked. A freshly created release key normally
**cannot upgrade an existing debug-signed build** in place. Back up save data
and explicitly plan any reinstall. Android signing lineage/rotation and split
install edge cases require separate qualification; this tool is conservative.

Then run the existing `./devtoolw device` only on an explicitly designated
non-production test device, after user review; the M3B preflight alone is **not
proof of instrumentation or gameplay success**.

## Evidence and limitations

`M3B_CANDIDATE_PROVENANCE.json` records source commit, GitHub run ID, package,
version, artifact digest and pinned signing-certificate match. This is
**self-reported CI evidence**, not an independently signed attestation, SLSA
provenance, reproducible build proof, or completed device qualification.

For trustworthy promotion, independently correlate Devtool's run/ref SHA,
artifact hash, certificate, device results and gameplay test evidence; design a
separately reviewed publication gate. Do not silently promote this candidate.

## M3A CI parser repair included

The M3A branch-push build of commit `506b9164123069479874893aaed75031df777a45`
completed Gradle build, JVM tests and Android Lint, but its evidence generation
failed while parsing the APK signing certificate. M3B updates the evidence
parser to accept verified `apksigner` outputs with colon-separated or wrapped
SHA-256 values and debug CN fields in non-leading order. It still requires
exactly one signing identity and rejects unexpected debug certificate CNs.
The repair is covered by offline Python regression fixtures; its Android CI
qualification remains pending until the M3B push.
