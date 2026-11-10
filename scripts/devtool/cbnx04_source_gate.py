#!/usr/bin/env python3
"""CB-NX04A: verify all local evidence, Android roster and non-mutating bridge contracts."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def source(path):
    f=ROOT/path
    assert f.is_file() and not f.is_symlink(), 'CBNX04_SOURCE_MISSING:'+path
    return f.read_text(encoding='utf8')
mods='app/src/main/java/com/sdvsync/mods/'
authority=source(mods+'NexusPairingAuthority.kt')
bridge=source(mods+'NexusPairingBridge.kt')
proof=source(mods+'NexusArchiveProvenance.kt')
runner=source('scripts/devtool/cbnx04_emulator_ci.sh')
receipt=source('scripts/devtool/cbnx04_instrumentation_receipt.py')
workflow=source('.github/workflows/cbnx04-authority.yml')
tests=source('app/src/androidTest/java/com/sdvsync/mods/CbNx04AuthorityDeviceTest.kt')
for marker in ('internal object NexusPairingAuthority', 'fun snapshot(records:',
               'Files.isSymbolicLink(modsDir.toPath())', 'Files.isSymbolicLink(folder.toPath())',
               'Files.isSymbolicLink(manifest.toPath())', 'MAX_MANIFEST_BYTES', 'MAX_FOLDERS',
               'folder.name.startsWith(".")', 'getOrPut(nexusId)', 'uniqueId.matches(id)',
               '"UNAVAILABLE"', '"QUALIFIED"', '"AMBIGUOUS"', '"DISABLED_PRESENT"',
               '.put("exact_file_installed", "UNKNOWN")', '.put("update_state", update.status)',
               '.put("archive_checksum_qualified", verified)', '.put("remote_update_check", freshness)',
               'records.filter { it.source == "nexus"', 'val reportableDownload = setOf('):
    assert marker in authority, 'CBNX04_EVIDENCE_CONTRACT_MISSING:'+marker
for forbidden in ('listInstalledMods(', 'renameTo(', 'deleteRecursively(', 'startDownload(',
                  'installFromZip(', 'ModDownloadService(', 'getDownloadUrl(', 'SharedPreferences(',
                  'setHandoffEnabled(', 'Environment.getExternalStorageDirectory('):
    assert forbidden not in authority, 'CBNX04_READONLY_MUTATION_REGRESSION:'+forbidden
assert 'NexusPairingAuthority.snapshot(' in bridge and 'ModDownloadJournal(context).list()' in bridge
assert 'NexusArchiveProvenance.inspect(records, privateReviewRoot)' in authority
update_source=source(mods+'NexusUpdateEvidence.kt')
for marker in ('fun freshness(', 'fun classify(', 'SMAPI_CACHE_STALE', 'SMAPI_CACHE_FRESH',
               'CLOCK_INVALID', 'ModUpdatePolicy.assess(', 'obs.installedVersion != installedVersion'):
    assert marker in update_source, 'CBNX04C_UPDATE_POLICY_CONTRACT_MISSING:'+marker
assert 'readCachedSmapiEvidence()' in bridge
assert 'activeContext.set(null)' in bridge and 'getUpdateObservations()' in bridge
assert 'getLastUpdateCheck()' in bridge and 'withTimeout(3000L)' in bridge
for forbidden in ('startDownload(', 'checkDetailed(', 'httpClient.newCall(', 'ModDownloadService.start('):
    assert forbidden not in update_source and forbidden not in bridge, 'CBNX04C_BACKGROUND_PROVIDER_OR_MUTATION:'+forbidden
assert 'activePrivateReviewRoot.get()' in bridge and 'activePrivateReviewRoot.set(null)' in bridge
for word in ('MessageDigest.getInstance("SHA-256")', 'Files.isSymbolicLink',
             'expected = props.getProperty("sha256")', 'record.modId != mod',
             'record.fileId != file', 'actual != expected', 'confirmed.add(id)',
             'archive.length() != originalLength', 'LOCAL_ZIP_VS_APP_RECEIPT'):
    assert word in proof or word in authority, 'CBNX04B_PROOF_SECURITY_CONTRACT_MISSING:'+word
for forbidden in ('renameTo(', 'deleteRecursively(', 'installFromZip(', 'startDownload(',
                  'getDownloadUrl(', 'post(', 'SharedPreferences('):
    assert forbidden not in proof, 'CBNX04B_ARCHIVE_PROOF_MUTATING:'+forbidden
assert 'archive_proof_state' in authority and 'VERIFIED_AT_SCAN' in authority
assert 'exact_file_installed", "UNKNOWN"' in authority
assert "'qualification': 'CBNX04C_API36_SYNTHETIC_SMAPI_CACHE_EVIDENCE'" in receipt
assert 'method_events != 14' not in receipt, 'CBNX04B_STALE_EVENT_ROSTER'
assert "'test_count': 7 if ok else 0" not in receipt, 'CBNX04B_STALE_TEST_COUNT'

assert 'CinderboxPaths.MODS_DIR' in bridge
assert '"installed_inventory_qualified", false' in bridge, 'CBNX03_BACKWARD_COMPATIBILITY_LOST'
assert '"proof_kind", "journal_only"' in bridge
assert 'CbNx04AuthorityDeviceTest' in runner and 'api-level: 36' in workflow
assert 'cbnx04_source_gate.py' in workflow and 'cbnx04_negative_tests.py' in workflow
assert 'cbnx04_emulator_ci.sh' in workflow and 'cbnx04_instrumentation_receipt.py' in runner
methods=tuple(re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(',tests))
assert len(methods)==15 and len(set(methods))==15, 'CBNX04_EMULATOR_ROSTER_DRIFT'
for method in methods:
    assert "'"+method+"'" in receipt, 'CBNX04_MISSING_RECEIPT_METHOD:'+method
assert 'method_events != 30' in receipt and "block.get('numtests') != '15'" in receipt
assert "'test_count': 15 if ok else 0" in receipt
# CBNX04C HF01: the canonical API36 freshness fixture must test REAL elapsed
# arithmetic, not merely a timestamp with a large-looking absolute value.
expiry = tests.split('@Test fun expiredOrClockInvalidSmapiCacheCannotShowAnUpdate()', 1)
assert len(expiry) == 2, 'CBNX04C_EXPIRY_TEST_NOT_FOUND'
expiry_body = expiry[1].split('\n    @Test ', 1)[0]
for required in (
    'val checkedAt = 999_000L',
    'val fourHours = 4L * 60L * 60L * 1000L',
    'assertEquals(14_400_000L, fourHours)',
    'assertEquals(fourHours, NexusUpdateEvidence.FRESH_MS)',
    'checkedAt + fourHours, reviews(root), smapi(checkedAt)',
    'checkedAt + fourHours + 1L, reviews(root), smapi(checkedAt)',
    '"SMAPI_CACHE_FRESH"', '"SMAPI_CACHE_STALE"',
    '"CLOCK_INVALID"', '"NEWER"', '"UNKNOWN"',
    'assertFalse(item(expired).has("candidate_version"))',
    'assertFalse(item(clock).has("candidate_version"))',
):
    assert required in expiry_body, 'CBNX04C_STALE_TIMESTAMP_FIXTURE:' + required
assert 'root, 15_000_000L,' not in expiry_body, 'CBNX04C_BAD_OLD_EXPIRY_TIMESTAMP'
unit = source('app/src/test/java/com/sdvsync/mods/NexusUpdateEvidenceTest.kt')
assert 'fun fourHoursIsInclusiveAndNextMillisecondIsStale()' in unit
assert 'checkedAt + fourHours + 1L' in unit
assert 'checkedAt + fourHours)' in unit
assert 'assertEquals(fourHours, NexusUpdateEvidence.FRESH_MS)' in unit
assert len(re.findall(r'@Test\s+fun\s+[A-Za-z_0-9]+\s*\(', unit)) == 6
print('CBNX04C_HF01_ACTUAL_ELAPSED_BOUNDARY_SOURCE_CONTRACT_PASS')

print('CBNX04C_CANONICAL_FRESH_SMAPI_FIFTEEN_METHOD_ROSTER_PASS')
