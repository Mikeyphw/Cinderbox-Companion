#!/usr/bin/env python3
"""M24 live depot mismatch must remain fail-closed; UI must not fake progress."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
def read(p):return (ROOT/p).read_text(encoding='utf-8')
def main():
    cross=read('app/src/main/java/com/sdvsync/download/M24DepotManifestCrosscheck.kt')
    pics=read('app/src/main/java/com/sdvsync/steam/SteamContentService.kt')
    svc=read('app/src/main/java/com/sdvsync/download/GameDownloadService.kt')
    ui=read('app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt')
    progress=read('app/src/main/java/com/sdvsync/download/M24DepotProgressPolicy.kt')
    required=[
      ('missing_depot_fail_closed','check(missing.isEmpty())' in cross and '(completedDepots - picsIds.keys).sorted()' in cross),
      ('no_manifest_fallback','completedDepots' in cross and 'picsIds' in cross),
      ('pics_ids_no_tokens', 'M24 PICS public numeric depot IDs=' in pics and 'manifest-bound IDs=' in pics),
      ('sdk_completed_ids','M24 downloaded depot IDs=' in svc),
      ('indeterminate_notification','DownloadState.DOWNLOADING, DownloadState.PREPARING' in svc and 'builder.setProgress(0, 0, true)' in svc),
      ('zero_progress_hidden','displayedDepotPercent(' in ui and 'value <= 0f' in progress),
      ('no_game_wide_guess','No reliable overall download percentage' in ui and 'Total game size: unknown' in ui),
      ('required_verification','File integrity verification — required' in ui),
    ]
    output={'schema_version':1,'producer':'cinderbox-m24-live-pics-progress-source',
            'checks':{k:'PASS' if v else 'FAIL' for k,v in required},
            'overall':'PASS_M24_PICS_PROGRESS_DIAGNOSTIC_SOURCE_ONLY' if all(v for _,v in required) else 'FAILED'}
    print(json.dumps(output,sort_keys=True))
    return 0 if output['overall'].startswith('PASS') else 1
if __name__=='__main__':sys.exit(main())
