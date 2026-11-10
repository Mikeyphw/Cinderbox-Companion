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
runner=source('scripts/devtool/cbnx04_emulator_ci.sh')
receipt=source('scripts/devtool/cbnx04_instrumentation_receipt.py')
workflow=source('.github/workflows/cbnx04-authority.yml')
tests=source('app/src/androidTest/java/com/sdvsync/mods/CbNx04AuthorityDeviceTest.kt')
for marker in ('internal object NexusPairingAuthority', 'fun snapshot(records:',
               'Files.isSymbolicLink(modsDir.toPath())', 'Files.isSymbolicLink(folder.toPath())',
               'Files.isSymbolicLink(manifest.toPath())', 'MAX_MANIFEST_BYTES', 'MAX_FOLDERS',
               'folder.name.startsWith(".")', 'getOrPut(nexusId)', 'uniqueId.matches(id)',
               '"UNAVAILABLE"', '"QUALIFIED"', '"AMBIGUOUS"', '"DISABLED_PRESENT"',
               '.put("exact_file_installed", "UNKNOWN")', '.put("update_state", "UNKNOWN")',
               '.put("archive_checksum_qualified", false)', '.put("remote_update_check", "NOT_PERFORMED")',
               'records.filter { it.source == "nexus"', 'val reportableDownload = setOf('):
    assert marker in authority, 'CBNX04_EVIDENCE_CONTRACT_MISSING:'+marker
for forbidden in ('listInstalledMods(', 'renameTo(', 'deleteRecursively(', 'startDownload(',
                  'installFromZip(', 'ModDownloadService(', 'getDownloadUrl(', 'SharedPreferences(',
                  'setHandoffEnabled(', 'Environment.getExternalStorageDirectory('):
    assert forbidden not in authority, 'CBNX04_READONLY_MUTATION_REGRESSION:'+forbidden
assert 'NexusPairingAuthority.snapshot(' in bridge and 'ModDownloadJournal(context).list()' in bridge
assert 'CinderboxPaths.MODS_DIR' in bridge
assert '"installed_inventory_qualified", false' in bridge, 'CBNX03_BACKWARD_COMPATIBILITY_LOST'
assert '"proof_kind", "journal_only"' in bridge
assert 'CbNx04AuthorityDeviceTest' in runner and 'api-level: 36' in workflow
assert 'cbnx04_source_gate.py' in workflow and 'cbnx04_negative_tests.py' in workflow
assert 'cbnx04_emulator_ci.sh' in workflow and 'cbnx04_instrumentation_receipt.py' in runner
methods=tuple(re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(',tests))
assert len(methods)==7 and len(set(methods))==7, 'CBNX04_EMULATOR_ROSTER_DRIFT'
for method in methods:
    assert "'"+method+"'" in receipt, 'CBNX04_MISSING_RECEIPT_METHOD:'+method
assert 'method_events != 14' in receipt and "block.get('numtests') != '7'" in receipt
assert "'test_count': 7 if ok else 0" in receipt
print('CBNX04_READONLY_EVIDENCE_SOURCE_AND_SEVEN_METHOD_ROSTER_PASS')
