#!/usr/bin/env python3
"""CB-NX01 source-only gate. Does not certify Nexus authentication or real device delivery."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def required_tokens(path, tokens):
    src = (ROOT / path).read_text(encoding='utf-8')
    missing = [token for token in tokens if token not in src]
    if missing: raise SystemExit(f'CBNX01_SOURCE_REFUSED:{path}:{missing}')

required_tokens('app/src/main/java/com/sdvsync/mods/api/NxmUriPolicy.kt',
                ['"nxm"', '"stardewvalley"', 'pathPattern.matchEntire', 'MAX_FUTURE_SECONDS', 'params["key"]'])
required_tokens('app/src/main/java/com/sdvsync/mods/api/NexusBrowserHandoff.kt',
                ['cinderbox_file=$fileId', 'cinderbox_mode=nxm', 'cinderbox_request=$requestId'])
required_tokens('app/src/main/java/com/sdvsync/MainActivity.kt',
                ['NxmUriPolicy.parse(uri.toString())', 'nxmInFlight.compareAndSet(false, true)',
                 'nxmInFlight.set(false)', 'downloadManager.startDownload(url, modName, parsed.modId, "nexus")'])
required_tokens('app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt',
                ['cbnx01.browser-handoff', 'NexusBrowserHandoff.forFile(mod.modId, file.fileId)',
                 'NexusBrowserLauncher.open(context, url)',
                 'onDownloadForReview(file.fileId)'])
required_tokens('app/src/main/java/com/sdvsync/mods/api/NexusBrowserLauncher.kt',
                ['org.mozilla.firefox', 'org.mozilla.firefox_beta', 'Intent.ACTION_VIEW'])
required_tokens('app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt',
                ['mapDownloadError(e.message, fileId)', 'NexusBrowserHandoff.forFile(modId, fileId)'])
required_tokens('app/src/main/java/com/sdvsync/mods/ModDownloadManager.kt',
                ['@Synchronized', 'ModDownloadState.DOWNLOADING', 'ModDownloadService.start('])
required_tokens('app/src/main/java/com/sdvsync/mods/ModDownloadService.kt',
                ['ModReviewQueue(filesDir).enqueue(', 'Stage for mandatory review'])
required_tokens('app/src/test/java/com/sdvsync/mods/api/CbNx01HandoffTest.kt',
                ['selectedModAndFileRemainInBrowserHandoff', 'onlyValidNxmMayStartDownload'])
print('CBNX01_CINDERBOX_SOURCE_PASS_RUNTIME_NOT_QUALIFIED')
