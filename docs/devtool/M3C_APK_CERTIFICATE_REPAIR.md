# M3C — Verified APK signing-block certificate evidence

M3A and M3B branch-push workflows (`38436414684`, `38439364223`,
`38444934113`) passed Gradle but failed at debug APK provenance with
`Could not establish exactly one Android APK signing identity`. The
original check parsed `apksigner --print-certs` human-readable text, a
fragile dependency across tool versions and output formatting.

M3C keeps **`apksigner verify --print-certs` as a mandatory cryptographic
verification gate**. After that successful exit status, it obtains the leaf
X.509 DER certificate directly from the APK's v2/v3 signing block and takes
its SHA-256. The reader requires one signer in each present scheme, bounded
records, and consistent cert hashes across schemes. For debug evidence,
OpenSSL decodes the leaf subject and must find `CN=Android Debug`. A malformed,
unsigned, conflicting, or unverified artifact is rejected. The signed
candidate path uses the same DER reader and still requires its exact
source-controlled SHA-256 fingerprint from M3B policy.

The DER parser alone is **not** a signature authenticator: any use outside
these guarded calls MUST separately run `apksigner verify` successfully.

## Validate on Termux

```sh
python3 -m unittest discover -s scripts/devtool -p 'test_m3_*.py' -v
python3 -m unittest discover -s scripts/devtool -p 'test_m3b_*.py' -v
python3 scripts/devtool/m3_build_evidence.py source
python3 scripts/devtool/m3b_release_candidate.py require-enabled
./devtoolw security
```

The optional real-APK fixture test runs only when `CINDERBOX_M3_TEST_APK`
points to an existing signed APK. It tests extraction, not verification of
cryptographic signatures; actual CI performs `apksigner verify` first.

## Promotion sequence (manual; not performed by patch)

1. Push M3C to `security/m0-m1-hardening` and require a **successful** `Build
   Debug APK` run at the new commit, with `M3_PROVENANCE.json` uploaded.
2. Protect `master` and configure the `release-signing` GitHub environment
   with master-only deployment restrictions and independent review where
   available. Verify the three environment secrets are configured; never
   print or upload them.
3. After code review, merge the complete security branch **via PR** to
   `master`. M3B signed-candidate workflow and its enabled pinned policy must
   be merged together, not registered separately.
4. Manually dispatch `Cinderbox Signed Candidate` with confirmation string
   `SIGNED_CANDIDATE` on `master`. Approve the environment gate as configured.
5. Verify the downloaded APK's SHA-256, `M3B_CANDIDATE_PROVENANCE.json`,
   pinned certificate, then run the read-only device upgrade preflight.

This workflow does not publish a GitHub Release, install apps, or establish
release/device qualification. **Debug and signed candidate signing keys
cannot be assumed to allow in-place upgrades of each other.**
