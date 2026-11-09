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
                 'nxmInFlight.set(false)', 'downloadManager.startDownload(url, modName, parsed.modId, "nexus", parsed.fileId)'])
required_tokens('app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt',
                ['cbnx01.browser-handoff', 'NexusBrowserHandoff.createUrl(mod.modId, file.fileId)',
                 'NexusBrowserLauncher.open(context, url)',
                 'onDownloadForReview(file.fileId)'])
required_tokens('app/src/main/java/com/sdvsync/mods/api/NexusBrowserLauncher.kt',
                ['io.github.forkmaintainers.iceraven', 'org.mozilla.firefox',
                 'org.mozilla.firefox_beta', 'Intent.ACTION_VIEW'])
required_tokens('app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt',
                ['mapDownloadError(e.message, fileId)', 'NexusBrowserHandoff.createUrl(modId, fileId)'])
required_tokens('app/src/main/java/com/sdvsync/mods/ModDownloadManager.kt',
                ['@Synchronized', 'ModDownloadService.start(', 'fileId: String = ""'])
required_tokens('app/src/main/java/com/sdvsync/mods/ModDownloadService.kt',
                ['ModReviewQueue(filesDir).enqueue(', 'fileManager.previewFromZip(tmp)',
                 'fileManager.installFromZip(tmp, preview.approvalKey)',
                 'ModDownloadPreferences.requiresApproval(this)'])
required_tokens('app/src/test/java/com/sdvsync/mods/api/CbNx01HandoffTest.kt',
                ['selectedModAndFileRemainInBrowserHandoff', 'onlyValidNxmMayStartDownload'])
# Q01 HF02 ID navigation: source-only contract; Kotlin JVM tests verify parsing.
required_tokens('app/src/main/java/com/sdvsync/mods/api/NexusIdJumpPolicy.kt',
                ['object NexusIdJumpPolicy', 'positiveId.matches', 'fileId'])
required_tokens('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt',
                ['cbnx01.mods.open-by-id', 'cbnx01.id-lookup.mod',
                 'cbnx01.id-lookup.file', 'onOpenExactNexusSelection(target.modId, target.fileId)'])
required_tokens('app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt',
                ['cbnx01.id-lookup.result', 'cbnx01.detail.file-id-filter',
                 'visibleFiles', 'cbnx01.id-lookup.browser', 'File ID: ${file.fileId}'])
required_tokens('app/src/main/java/com/sdvsync/MainActivity.kt',
                ['route = "mod_detail/{modId}/{source}"',
                 'onOpenExactNexusSelection = { modId, fileId ->',
                 '.getStateFlow("cbnx01_selected_file_id", "").collectAsState()',
                 '?.set("cbnx01_selected_file_id", fileId)'])
# Q01 HF04 physical intent receipt: no URL, token, key or query parameter is logged.
required_tokens('app/src/main/java/com/sdvsync/MainActivity.kt', [
    'private const val NXM_DIAG_TAG = "CBNX01_NXM_RX"',
    '"NXM_RECEIVED_VIEW"', '"NXM_PARSE_REJECTED"', '"NXM_PARSE_ACCEPTED"',
    '"NXM_URL_RESOLUTION_STARTED"', '"NXM_RESOLUTION_OR_DOWNLOAD_FAILURE"',
    '"NXM_MANAGER_RETURNED_NOT_STAGED_PROOF"'])
print('CBNX01_Q01_HF02_DIRECT_ID_NAVIGATION_SOURCE_PASS')
print('CBNX01_CINDERBOX_SOURCE_PASS_RUNTIME_NOT_QUALIFIED')

