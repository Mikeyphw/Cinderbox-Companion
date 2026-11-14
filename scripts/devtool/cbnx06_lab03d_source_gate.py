#!/usr/bin/env python3
"""LAB03D app-private synthetic staging contracts; source-only, not physical proof."""
from __future__ import annotations
from pathlib import Path
import sys

if sys.flags.optimize:
    raise SystemExit('LAB03D_ASSERTIONS_REQUIRED')
ROOT=Path(__file__).resolve().parents[2]
STAGE='app/src/main/java/com/sdvsync/mods/NexusLab03DArchiveStage.kt'
POLICY='app/src/main/java/com/sdvsync/mods/NexusLab03DArchivePolicy.kt'
PANEL='app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt'
UNIT='app/src/test/java/com/sdvsync/mods/NexusLab03DArchivePolicyTest.kt'
WF='.github/workflows/cbnx06-lab03d-staged-archive.yml'
FULL='.github/workflows/cbnx06-full-cinderbox-lab.yml'

class Refused(ValueError): pass

def need(condition,reason):
    if not condition: raise Refused('LAB03D_'+reason)

def validate(stage,policy,panel,unit,workflow,full):
    for name,code in {
        'ISOLATED_LAB_BUILD':'BuildConfig.CBNX_LAB && BuildConfig.APPLICATION_ID == APP',
        'ISOLATED_PACKAGE':'context.packageName == APP',
        'LOCAL_PRIVACY_BOUNDARY':'CinderboxLabBoundary.requirePrivate(file)',
        'LAB_MODS_ROOT':'CinderboxLabBoundary.requireModsRoot(mods)',
        'SYNTHETIC_SOURCE':'NexusLab03Evidence.previewSynthetic(context)',
        'SYNTHETIC_RECEIPT':'sourceReceipt.readText()',
        'SOURCE_SHA':'sourceHash == preview.archiveSha256',
        'SOURCE_SOURCE_SHA':'saved.getString("source_sha256") == sourceHash',
        'STAGE_SHA':'digest(stage) == sourceHash',
        'SOURCE_SCHEMA':'NexusLab03DArchivePolicy.SOURCE_SCHEMA',
        'STAGE_SCHEMA':'NexusLab03DArchivePolicy.STAGE_SCHEMA',
        'CORRUPTION_REFUSAL':'LAB03D_STAGE_CHANGED',
        'PARTIAL_STAGE_REFUSAL':'LAB03D_PARTIAL_STAGE_REFUSED',
        'PRIVACY_SYMLINK':'Files.isSymbolicLink(file.toPath())',
        'STAGE_ATOMIC_MOVE':'StandardCopyOption.ATOMIC_MOVE',
        'NO_REPLACE':'check(!destination.exists())',
        'SINGLE_ARCHIVE_ENTRY':'zip.nextEntry == null',
        'ARCHIVE_ENTRY_MATCH':'entry.name == NexusLab03DArchivePolicy.ENTRY',
        'SYNTHETIC_MANIFEST':'CBNX06.LAB03.Synthetic',
        'SOURCE_PROVENANCE_FALSE':'!previous.getBoolean("nexus_file_provenance_verified")',
        'STAGE_PROVENANCE_FALSE':'.put("nexus_file_provenance_verified", false)',
        'STAGE_INSTALLED_FALSE':'.put("installed", false)',
        'PRODUCTION_NOT_EXAMINED':'.put("production_files_examined", false)',
        'MODS_SNAPSHOT':'check(before == snapshot())',
        'BOTH_FILES_REPLAY':'stage.exists() == receipt.exists()',
        'STAGED_SOURCE_SHA':'saved.getString("source_sha256") == sourceHash',
        'STAGE_RECEIPT_POLICY':'NexusLab03DArchivePolicy.validLocalReceipt(',
        'EXPLICIT_ENTRY':'@Synchronized fun stageSynthetic(context: Context)',
    }.items(): need(code in stage,'MISSING_STAGE_CONTRACT:'+name)
    need(stage.count('Files.move(')==1,'MULTIPLE_STAGE_MOVES')
    need(stage.count('digest(stage) == sourceHash')==2,'STAGE_DIGEST_GUARD_DRIFT')
    for forb in ('getDownloadUrl(', 'ModDownloadService(', 'installFromZip(',
                 'startDownload(', 'android.permission.', 'http://', 'https://',
                 'NexusPairingInbox.admit(', 'NexusPairingBridge.setHandoffEnabled(',
                 'CinderboxPaths.SAVES_DIR', 'File("/storage'):
        need(forb not in stage,'UNSAFE_STAGE_CAPABILITY:'+forb)
    for name,code in {
        'SHA256_HEX':'Regex("[0-9a-f]{64}")',
        'LOCAL_SCHEMA':'cbnx06-lab03d-staged-synthetic-v1',
        'LOCAL_SCOPE':'LAB_SYNTHETIC_ONLY',
        'LOCAL_PROVENANCE':'LOCAL_SYNTHETIC_GENERATOR_ONLY',
        'EXPECTED_ZIP_ENTRY':'CBNX06_LAB03_ONLY/manifest.json',
        'SOURCE_SIZE_MIN':'MIN_ARCHIVE_BYTES = 128L',
        'SOURCE_SIZE_MAX':'MAX_ARCHIVE_BYTES = 16_384L',
        'SOURCE_BYTE_MATCH':'sourceBytes == stagedBytes',
        'SOURCE_HASH_MATCH':'sourceSha256 == stagedSha256',
        'NO_NEXUS_CLAIM':'!nexusVerified',
        'NO_INSTALL_CLAIM':'!installed',
        'NO_PROD_CLAIM':'!productionFilesExamined',
    }.items(): need(code in policy,'MISSING_POLICY_CONTRACT:'+name)
    for code in ('NexusLab03DArchiveStage.stageSynthetic(context)',
                 'cbnx06.lab03d.stage-synthetic','cbnx06.lab03d.stage-feedback',
                 'Stage and verify synthetic archive (LAB only)',
                 'if (BuildConfig.CBNX_LAB) {'):
        need(code in panel,'MISSING_UI_CONTRACT:'+code)
    need(panel.count('NexusLab03DArchiveStage.stageSynthetic(context)')==1,
         'DUPLICATE_STAGING_SINK')
    need(panel.index('NexusLab03DArchiveStage.stageSynthetic(context)') <
         panel.index('Text("Exact-file requests"'), 'STAGE_UI_AFTER_REMOTE_INBOX')
    need('NexusLab03DArchiveStage.stageSynthetic(context)' not in
         panel[panel.index('for (item in pending)'):], 'REMOTE_INBOX_CAN_TRIGGER_STAGE')
    for code in ('@Test fun permitsOnlyBoundedSourceMatchedLocalSyntheticEvidence()',
                 '@Test fun refusesProvenanceEscalation()',
                 '@Test fun refusesHashAndSizeDrift()'):
        need(code in unit,'JVM_TEST_MISSING:'+code)
    for code in ('test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"',
                 'python3 -B scripts/devtool/cbnx06_lab03d_source_gate.py',
                 'python3 -B scripts/devtool/cbnx06_lab03d_tests.py',
                 ':app:testDebugUnitTest :app:assembleCbnxLab',
                 'persist-credentials: false'):
        need(code in workflow,'DEDICATED_CI_MISSING:'+code)
    for code in ("      - 'scripts/devtool/cbnx06_lab03d_*.py'",
                 'python3 -B scripts/devtool/cbnx06_lab03d_source_gate.py',
                 'python3 -B scripts/devtool/cbnx06_lab03d_tests.py',
                 ':app:assembleCbnxLab'):
        need(code in full,'FULL_LAB_CI_MISSING:'+code)
    need('LAB03B physical' not in policy and 'downloaded' not in stage,
         'PHYSICAL_OR_PROVIDER_CLAIM')
    return True

def read(path):
    p=ROOT/path
    need(p.is_file() and not p.is_symlink(),'SOURCE_MISSING_OR_LINKED:'+path)
    return p.read_text(encoding='utf8')

def main():
    validate(*(read(p) for p in (STAGE,POLICY,PANEL,UNIT,WF,FULL)))
    print('LAB03D_SOURCE_STAGE_BOUNDED_PRIVATE_SYNTHETIC_ONLY_PASS')
    print('LAB03D_SOURCE_SHA256_PROVENANCE_NO_NETWORK_NO_INSTALL_PASS')

if __name__=='__main__':
    try: main()
    except (Refused,AssertionError,OSError) as e:
        print('LAB03D_SOURCE_REFUSED:'+str(e),file=sys.stderr)
        raise SystemExit(2)
