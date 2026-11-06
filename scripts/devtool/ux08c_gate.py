#!/usr/bin/env python3
"""UX-08C save + backup native overviews: read-only routing and source/security check."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]

def source(path:str,root:Path=ROOT)->str:
    f=root/path
    assert f.is_file() and not f.is_symlink(), 'UX08C_MISSING:'+path
    return f.read_text(encoding='utf8')

def check(root:Path=ROOT)->dict:
    main=source('app/src/main/java/com/sdvsync/MainActivity.kt',root)
    saves=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt',root)
    detail=source('app/src/main/java/com/sdvsync/ui/screens/ApprovedSaveDeepScreen.kt',root)
    dashboard=source('app/src/main/java/com/sdvsync/ui/viewmodels/DashboardViewModel.kt',root)
    backupvm=source('app/src/main/java/com/sdvsync/ui/viewmodels/BackupListViewModel.kt',root)
    original_viewer=source('app/src/main/java/com/sdvsync/ui/screens/SaveViewerScreen.kt',root)
    original_backup=source('app/src/main/java/com/sdvsync/ui/screens/BackupListScreen.kt',root)
    original_sync=source('app/src/main/java/com/sdvsync/ui/screens/SyncDetailScreen.kt',root)
    device=source('app/src/androidTest/java/com/sdvsync/qualification/UX08CSaveReviewDeviceTest.kt',root)
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    coordinator=source('app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',root)
    assert main.count('route = "save_review/{saveFolderName}"') == 1
    assert main.count('route = "backup_review/{saveFolderName}"') == 1
    assert main.count('route = "save_viewer/{saveFolderName}"') == 1
    assert main.count('route = "backups/{saveFolderName}"') == 1
    assert main.count('route = "sync_detail/{saveFolderName}/{hasCloud}/{hasLocal}"') == 1
    for fragment in ('ApprovedSaveDeepScreen(', 'SaveDeepArea.SAVE_REVIEW',
        'SaveDeepArea.BACKUP_REVIEW', 'Uri.encode(saveFolderName)',
        'onOpenSaveReview = { folderName ->',
        'onOpenSave = { folderName -> parentNavController.navigate("save_viewer/${Uri.encode(folderName)}") }',
        'onOpenBackups = { folderName -> parentNavController.navigate("backups/${Uri.encode(folderName)}") }',
        'SaveViewerScreen(', 'BackupListScreen(', 'SyncDetailScreen('):
        assert fragment in main,'UX08C_NAVIGATION_DRIFT:'+fragment
    assert 'onOpenSaveReview: (String) -> Unit = {}' in saves
    assert 'cinderbox.saves.review-detail' in saves
    for fragment in ('SaveDeepSnapshot', 'SaveDeepArea.SAVE_REVIEW', 'SaveDeepArea.BACKUP_REVIEW',
        'dashboardViewModel.refresh()', 'backupsViewModel.loadBackups(saveFolderName)',
        'dashboard.saves.singleOrNull { it.folderName == saveFolderName }',
        'backups.backups.size', 'cinderbox.screen.save-review',
        'cinderbox.screen.backup-review', 'cinderbox.save-deep.viewer',
        'cinderbox.save-deep.backup-review', 'cinderbox.save-deep.sync-review',
        'cinderbox.save-deep.backups-advanced',
        'not proof that a restore will succeed', 'No transfer begins from this overview'):
        assert fragment in detail,'UX08C_EVIDENCE_OR_ACTION_MISSING:'+fragment
    assert 'data class SaveEntry(' in dashboard and 'val hasLocal: Boolean' in dashboard
    assert 'fun loadBackups(saveFolderName: String)' in backupvm
    assert 'fun restoreBackup(backupDir: File)' in backupvm
    assert 'fun SaveViewerScreen(' in original_viewer
    assert 'fun BackupListScreen(' in original_backup
    assert 'fun SyncDetailScreen(' in original_sync
    assert 'class UX08CSaveReviewDeviceTest' in device
    assert device.count('@Test fun ')==3
    assert 'assertDoesNotExist()' in device
    for forbidden in ('restoreBackup(', 'confirmImport(', 'requestSyncPreview(', 'performSync(',
                      'deleteRecursively(', 'java.io.File(', 'startDownload(',
                      'requestShizukuPermission(', 'setFileAccessMode(', 'Runtime.getRuntime(',
                      '/storage/emulated/'):
        assert forbidden not in detail, 'UX08C_UNSAFE_OVERVIEW:'+forbidden
    for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[k] is False,'UX08C_RELEASE_GUARD:'+k
    assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator
    assert 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator
    return {'result':'UX08C_SAVE_AND_BACKUP_READ_ONLY_SOURCE_PASS',
            'existing_guarded_routes_preserved':True,'steam_optional':True,
            'automatic_restore':False,'automatic_sync':False,'physical_device_qualified':False,
            'pixel_parity_verified':False,'release_enabled':False}
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
