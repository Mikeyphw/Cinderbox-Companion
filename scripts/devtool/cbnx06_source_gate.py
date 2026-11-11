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
              'SOURCE_ATTESTATION.json','retention-days: 7',
              "physical_arm64_qualified':False","live_nexus_qualified':False"):
    assert token in w,'CBNX06_HOSTED_CONTRACT_STALE:'+token
for token in ('--resume-only', '--full-mods-hash','run-as', 'physical device',
              'Nexus', 'Firefox', 'NO auto-install', 'rollback'):
    assert token.lower() in d.lower(),'CBNX06_DOC_INCOMPLETE:'+token
assert len(re.findall(r'^    def test_',t,re.M))==25,'CBNX06_EXPECTED_25_TESTS'
ast.parse(a);ast.parse(t)
print('CBNX06_READ_ONLY_SOURCE_AND_HOSTED_ARTIFACT_CONTRACT_PASS')
