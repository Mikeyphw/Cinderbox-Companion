#!/usr/bin/env python3
"""CB-NX02 — new download UX, safety and privacy source contract. Android runtime remains separately gated."""
from pathlib import Path
import json, re
ROOT = Path(__file__).resolve().parents[2]

def text(path):
    file = ROOT/path
    assert file.is_file() and not file.is_symlink(), 'CBNX02_MISSING:'+path
    return file.read_text(encoding='utf8')

def require(path, words):
    src=text(path)
    for word in words:
        assert word in src, 'CBNX02_MISSING_TOKEN:'+path+':'+word
    return src

MOD='app/src/main/java/com/sdvsync/mods/'
SCREENS='app/src/main/java/com/sdvsync/ui/screens/'
require(MOD+'ModDownloadPreferences.kt', [
    'getBoolean(APPROVAL, false)', 'putBoolean(APPROVAL, enabled)', 'commit()'])
service=require(MOD+'ModDownloadService.kt', [
    'ModDownloadPreferences.requiresApproval(this)',
    'fileManager.previewFromZip(tmp)',
    'fileManager.installFromZip(tmp, preview.approvalKey)',
    'ModReviewQueue(filesDir).enqueue(',
    'downloaded && !retainedForReview', 'postResultNotification(',
    'cinderbox_open_downloads', 'cinderbox_download_job_id',
    'resultIdFor(jobId)', 'val safeFailure = when (phase)',
    'if (received > MAX_ARCHIVE_BYTES)',
    'queue.addLast(next)', 'queue.removeFirst()'])
assert service.index('fileManager.previewFromZip(tmp)') < service.index('fileManager.installFromZip(tmp, preview.approvalKey)')
assert 'putExtra(EXTRA_URL, url)' in service and 'journal.update(item.id' in service
review=require(MOD+'ModSafety.kt', [
    'mod-review-pending.zip', 'mod-review-pending.properties',
    'mod-review-backlog', 'fun promoteIfNeeded()', 'fun pendingCount()',
    'setProperty("file_id", fileId)', 'setProperty("sha256", digestHex)',
    'setProperty("job_id", jobId.take(64))',
    'val expected = receipt().sha256', 'file.takeIf { actual == expected }'])
ledger=require(MOD+'ModDownloadJournal.kt', [
    'fileId: String', '"QUEUED"', '"INSTALLED"', '"REVIEW_REQUIRED"',
    'markInterrupted()', 'fun clearHistory()', 'cancelIfActive(', 'take(60)'])
# Inspect the actual persisted fields, not comments or log lines. URL credentials must remain ephemeral.
assert not re.search(r'\.put\("(?:url|nxm|key|expires|token|cookie|downloadUrl)"', ledger)
assert not re.search(r'setProperty\("(?:url|nxm|key|expires|token|cookie|downloadUrl)"', review)
require('app/src/main/java/com/sdvsync/MainActivity.kt', [
    'ModDownloadsScreen(', 'SnackbarHost(hostState = snackbar',
    'startDownload(url, modName, parsed.modId, "nexus", parsed.fileId)',
    'cinderbox_open_downloads', 'highlightedDownloadJobId'])
require('app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt', [
    'downloadManager.startDownload(url, modName, modId, source, fileId)'])
# CBNX02's queued downloads must not be blocked by another job's progress.
# Retain single-flight resolution through the ViewModel's atomic guard.
detail=require(SCREENS+'ApprovedModDetailScreen.kt', [
    'onDownloadForReview = viewModel::installFile',
    'requestInFlight = state.isDownloading',
    'val downloadBusy = requestInFlight', 'val busy = requestInFlight',
    'nex.r5.download-for-review', 'onDownloadForReview(file.fileId)'])
assert 'val downloadBusy = requestInFlight ||' not in detail, 'CBNX02_GLOBAL_BUSY_LOCK_REGRESSION'
assert 'val busy = requestInFlight ||' not in detail, 'CBNX02_FILE_BUSY_LOCK_REGRESSION'
vm=text('app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt')
assert 'downloadLinkRequest.compareAndSet(false, true)' in vm, 'CBNX02_LINK_SINGLEFLIGHT_LOST'
require(SCREENS+'ModDownloadsScreen.kt', [
    'cbnx02.downloads.review', 'cbnx02.downloads.job',
    'cbnx02.downloads.approval-toggle', 'onOpenMod', 'journal.clearHistory()',
    'reviewModel.confirmPendingReview()', 'isReviewHead = record.id == reviewHead.jobId',
    'record.id == selectedJobId', 'statusBarsPadding().navigationBarsPadding()',
    'previewMatchesCurrentArchive && reviewCount > 0'])
require(SCREENS+'ApprovedModsScreen.kt', ['cbnx02.mods.download-activity'])
require(SCREENS+'SettingsScreen.kt', ['cbnx02.settings.require-approval'])
require('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt', [
    'pendingFileId', 'pendingDigest', 'ModDownloadJournal(context).update('])
require('app/src/androidTest/java/com/sdvsync/ui/screens/CbNx02DownloadsUiDeviceTest.kt', [
    'exactFileReviewCardOpensRealReviewRoute', 'activeCardShowsBytesAndExplicitCancelAllAction',
    'backlogCardCannotApproveDifferentFile'])
require('app/src/androidTest/java/com/sdvsync/mods/CbNx02DownloadUxDeviceTest.kt', [
    'approvalCanBeDisabledAndRestored', 'queuedReviewPreservesExactFileIdsAndPromotesNext',
    'journalRetainsFileIdentityWithoutBearerUrl',
    'stagedArchiveChecksumRejectsTamperingWithoutInstalling',
    'terminalInstallIsNotOverwrittenByServiceCancellation'])
require('scripts/devtool/cbnx02_emulator_ci.sh', ['CbNx02DownloadsUiDeviceTest'])
policy=json.loads(text('docs/security/M3_RELEASE_POLICY.json'))
for field in ('release_enabled','publication_enabled', 'automatic_device_install',
              'device_qualification_complete'):
    assert policy[field] is False, 'CBNX02_RELEASE_POLICY_CHANGED:'+field
# CB-NX02B: per-item controls are bounded by local job IDs, and crash recovery
# never reuses an expiring Nexus credential or assumes that installation finished.
require(MOD+'ModQueueControlPolicy.kt', [
    'fun canPause(', 'fun canCancel(', 'fun canResumeInSession(',
    'fun validMove(', 'fun freshLinkAllowed(', 'positiveId.matches(modId)',
    'positiveId.matches(fileId)'])
require(MOD+'ModDownloadJournal.kt', [
    '"PAUSED"', '"INTERRUPTED"', '"VERIFY_REQUIRED"',
    'fun moveQueued(', 'fun resumePaused(', 'fun markJobInterrupted(',
    'if (old.none { it.status in active || it.status == "PAUSED" })',
    'Outcome unknown. Inspect installed Mods', 'queuePosition'])
assert '"VALIDATING", "INSTALLING" -> row.copy(status = "VERIFY_REQUIRED"' in ledger, 'CBNX02B_MISSING_UNCERTAIN_INSTALL_RECOVERY'
assert '"QUEUED", "DOWNLOADING", "PAUSED" -> row.copy(status = "INTERRUPTED"' in ledger, 'CBNX02B_MISSING_TRANSFER_REAUTH_RECOVERY'
require(MOD+'ModDownloadService.kt', [
    'ACTION_PAUSE_JOB', 'ACTION_RESUME_JOB', 'ACTION_CANCEL_JOB',
    'ACTION_MOVE_UP', 'ACTION_MOVE_DOWN', 'activeCall?.cancel()',
    'journal.resumePaused(id)', 'journal.moveQueued(id, delta)',
    'synchronized(workLock) { activePhase = "INSTALLING" }',
    'journal.markJobInterrupted(it)', 'ModReviewQueue(filesDir).enqueue('])
require(SCREENS+'ModDownloadsScreen.kt', [
    'cbnx02b.queue.pause', 'cbnx02b.queue.resume',
    'cbnx02b.queue.cancel-one', 'cbnx02b.queue.up',
    'cbnx02b.queue.down', 'cbnx02b.queue.retry-exact',
    'NexusBrowserHandoff.createUrl(record.modId, record.fileId)',
    'NexusBrowserLauncher.open(context, url)',
    'record.status == "VERIFY_REQUIRED"'])
require('app/src/test/java/com/sdvsync/mods/ModQueueControlPolicyTest.kt', [
    '@Test fun activeAndQueuedCanPauseButInstallationCannot()',
    '@Test fun freshLinkIsTiedToOriginalExactNexusIdentity()'])
require('app/src/androidTest/java/com/sdvsync/ui/screens/CbNx02BQueueControlsUiDeviceTest.kt', [
    'queuedCardMovesAndCancelsOnlyItsOwnJob',
    'interruptedCardCannotResumeWithoutNewNexusLink'])
assert 'putExtra(EXTRA_URL, url)' in service, 'CBNX02B_EXISTING_EPHEMERAL_URL_HANDOFF_LOST'
print('CBNX02_DOWNLOAD_UX_SOURCE_PASS_ANDROID_RUNTIME_PENDING')
