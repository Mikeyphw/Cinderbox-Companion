#!/usr/bin/env python3
"""CB-NX06 physical acceptance source gate; never upgrades synthetic evidence."""
from pathlib import Path
import ast
import re
import sys
if sys.flags.optimize:raise SystemExit('CBNX06_SOURCE_GATE_CANNOT_RUN_WITH_ASSERTIONS_DISABLED')

root=Path(__file__).resolve().parents[2]
w=(root/'.github/workflows/cbnx06-physical-read-only.yml').read_text()
a=(root/'scripts/devtool/cbnx06_physical_acceptance.py').read_text()
t=(root/'scripts/devtool/cbnx06_physical_acceptance_tests.py').read_text()
d=(root/'docs/CBNX06_PHYSICAL_ACCEPTANCE.md').read_text()
artifact=(root/'scripts/devtool/cbnx06_debug_artifact.py').read_text()
artifact_tests=(root/'scripts/devtool/cbnx06_hf01_artifact_tests.py').read_text()
for path,txt in [('acceptance',a),('tests',t),('workflow',w)]:
    assert txt and len(txt)>500, 'CBNX06_MISSING_SOURCE:'+path
for token in ("ACK = 'I_AUTHORIZE_READ_ONLY_DEVICE_PROBE'",'run-as',
              'PHYSICAL_ARM64_API36_REQUIRED_NO_EMULATOR',
              'INSTALLED_APK_DOES_NOT_MATCH_PINNED_DEBUG_ARTIFACT',
              'SOURCE_PIN_CHANGED_DURING_PHYSICAL_ACCEPTANCE',
              'REVIEW_ARCHIVE_CHECKSUM_MISMATCH','NO_NEW_EXACT_FILE_PAIRING_REQUEST',
              'PAIRING_REQUEST_IDENTITY_NOT_FRESH','MODS_CONTENT_CHANGED_BEFORE_REVIEW',
              "'live_nexus_qualified':False", "'release_qualified':False",
              'REUSED_PREEXISTING_JOURNAL_JOB','INVALID_BEFORE_RECEIPT',
              'EXACT_CI_DEBUG_APK_AND_SOURCE_ATTESTATION_FILES_REQUIRED',
              "meta.get('source_sha')!=args.cinderbox_sha",
              "meta.get('apk_sha256')!=expected"):
    assert token in a,'CBNX06_ACCEPTANCE_CONTRACT_STALE:'+token
for forbidden in ('adb install','adb uninstall','su -c','pm clear','pm grant',
                  'http://127.0.0.1:38471/v1/pair', 'requests.post(', 'urlopen('):
    assert forbidden not in a,'CBNX06_MUTATING_OR_NETWORK_PRIMITIVE:'+forbidden
for token in ('python3 -B scripts/devtool/cbnx06_physical_acceptance_tests.py',
              'python3 -B scripts/devtool/cbnx06_source_gate.py',
              ':app:assembleDebug',"cbnx06-exact-source-debug-apk",
              'retention-days: 7'):
    assert token in w,'CBNX06_HOSTED_CONTRACT_STALE:'+token
for token in ('--resume-only', '--full-mods-hash','run-as', 'physical device',
              'Nexus', 'Firefox', 'NO auto-install', 'rollback'):
    assert token.lower() in d.lower(),'CBNX06_DOC_INCOMPLETE:'+token
assert len(re.findall(r'^    def test_',t,re.M))==25,'CBNX06_EXPECTED_25_TESTS'
# HF01: do not assume app-debug.apk is the Gradle output. app/build.gradle.kts
# sets outputFileName to CinderboxCompanion-v$versionName.apk. Match the
# authoritative Gradle metadata and emit a stable attested artifact filename.
for required in ('metadata_path = debug_dir / "output-metadata.json"', 'variantName', 'applicationId',
                 'outputFile', 'CinderboxCompanion-v', 'MULTIPLE_OR_UNEXPECTED_APKS',
                 'GRADLE_OUTPUT_FILENAME_MISMATCH', 'COPIED_APK_SHA256_MISMATCH',
                 'SOURCE_ATTESTATION.json', 'SHA256SUMS',
                 'source_sha', 'physical_arm64_qualified', 'release_qualified'):
    assert required in artifact, 'CBNX06_HF01_ARTIFACT_SELECTOR_STALE:'+required
for required in ('cbnx06_debug_artifact.py',
                 'python3 -B scripts/devtool/cbnx06_hf01_artifact_tests.py',
                 '--debug-dir app/build/outputs/apk/debug',
                 '--output-dir "$RUNNER_TEMP/cbnx06-debug"',
                 '--source-sha "$CBNX06_EXPECTED_HEAD"'):
    assert required in w, 'CBNX06_HF01_WORKFLOW_STALE:'+required
# HF03: pin CI to the already-provisioned debug signing secret.
assert 'secrets.CINDERBOX_DEBUG_KEYSTORE_B64' in w, 'CBNX06_EXISTING_KEYSTORE_SECRET_NOT_REFERENCED'
assert 'secrets.CINDERBOX_DEBUG_KEYSTORE_BASE64' not in w, 'CBNX06_UNKNOWN_KEYSTORE_SECRET_REFERENCED'
assert "CINDERBOX_REQUIRE_PERSISTENT_DEBUG_SIGNING: 'true'" in w, 'CBNX06_PERSISTENT_SIGNING_NOT_MANDATORY'
assert 'test -s app/build/outputs/apk/debug/app-debug.apk' not in w, 'CBNX06_HF01_OLD_FIXED_APK_PATH'
assert len(re.findall(r'^    def test_', artifact_tests,re.M))>=14, 'CBNX06_HF01_TEST_ROSTER_STALE'
ast.parse(a);ast.parse(t);ast.parse(artifact);ast.parse(artifact_tests)
print('CBNX06_READ_ONLY_SOURCE_AND_HOSTED_ARTIFACT_CONTRACT_PASS')
