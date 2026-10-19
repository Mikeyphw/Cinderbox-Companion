#!/usr/bin/env python3
"""Source-bound M24 stage transparency, no manual storage-budget, and Android picker gate."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
    read=lambda name:(R/name).read_text(encoding="utf-8")
    ui=read('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt')
    vm=read('app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt')
    mgr=read('app/src/main/java/com/sdvsync/download/GameDownloadManager.kt')
    svc=read('app/src/main/java/com/sdvsync/download/GameDownloadService.kt')
    fp=read('app/src/main/java/com/sdvsync/download/M24DepotFileProof.kt')
    cross=read('app/src/main/java/com/sdvsync/download/M24DepotManifestCrosscheck.kt')
    picker=read('app/src/main/java/com/sdvsync/local/M24AndroidFolderPicker.kt')
    policy=read('app/src/main/java/com/sdvsync/local/M24FolderSelectionPolicy.kt')
    check={
       'budget_ui_gone':all(x not in ui for x in ('Storage budget','Estimated game download size','StoragePlanner.downloadPlan')),
       'no_steam_budget_state':all('estimatedPayloadBytes' not in x and 'estimatedGameSizeGiB' not in x for x in (svc,mgr,vm)),
       'write_and_protected_tree_gates': 'StoragePreflight.requireWritable(installRoot)' in svc and 'M23CinderboxFirstPolicy.assess' in svc and 'StoragePreflight.requireWritable(directory)' in mgr,
       'system_picker': 'rememberLauncherForActivityResult' in ui and 'ActivityResultContracts.OpenDocumentTree()' in ui and 'chooseAndroidFolder(uri)' in ui,
       'direct_file_only': 'DocumentsContract.isTreeUri(uri)' in picker and 'M24FolderSelectionPolicy.primaryRelativePath(' in picker and 'com.android.externalstorage.documents' in picker and 'takePersistableUriPermission(' in picker,
       'unsafe_id_fail_closed':all(x in policy for x in ('primary:', 'part != ".."','part.isNotBlank()')),
       'transparent_stages':all(x in svc for x in ('Checking Steam depot manifests','Rechecking Steam branch and depot identity','Publishing verified files atomically','Rechecking published Steam depot files','Completing recovery journal')),
       'not_overall_percent':'% of this step only' in ui and '100% of a step does not mean' in ui,
       'manifest_progress':'progress(index + 1, expected.size)' in fp and 'M24DepotFileProof.verify(stage, expected, progress)' in cross,
       'indeterminate_notification':'DownloadState.VERIFYING -> {' in svc and 'builder.setProgress(0, 0, true)' in svc,
       'no_release':'release_enabled = true' not in read('.devtool.toml')
    }
    receipt=dict(schema_version=1,producer='cinderbox-m24-verification-picker-source',checks={k:'PASS' if v else 'FAIL' for k,v in check.items()},overall='PASS_M24_VERIFY_PICKER_SOURCE_ONLY' if all(check.values()) else 'FAILED_OR_BLOCKED',device_qualified=False,steam_live_completed=False)
    print(json.dumps(receipt,sort_keys=True))
    return 0 if all(check.values()) else 1
if __name__=='__main__':raise SystemExit(main())
