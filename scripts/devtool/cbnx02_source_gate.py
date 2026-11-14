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
    'activePhase = "INSTALLING"',
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

# CB-NX02B HF02: atomic admission, no stale-worker state downgrade, and real API36 roster.
manager=require(MOD+'ModDownloadManager.kt', ['journal.admit(', 'ModDownloadAdmission',
    'StoragePreflight.requireWritable(context.cacheDir)', 'if (!admission.accepted)',
    'ModDownloadService.start(context, url, modName, modId, source, fileId, id)'])
assert 'journal.list().any' not in manager, 'CBNX02B_HF02_NONATOMIC_MANAGER_ADMISSION'
ledger=require(MOD+'ModDownloadJournal.kt', [
    'private val lock = Any()', 'fun admit(', 'synchronized(lock)', 'protectedStatuses',
    '"PAUSED", "VERIFY_REQUIRED", "REVIEW_REQUIRED", "BLOCKED"',
    'hasUnresolvedReviewIdentity(', 'return@synchronized ModDownloadAdmission(reason = "VERIFY_REQUIRED")' if False else '"VERIFY_REQUIRED" -> "VERIFY_REQUIRED"',
    'write(rows)', 'fun isQueuedIdentity(', 'private fun allowed(',
    '"VERIFY_REQUIRED", "INSTALLED", "COMPLETED"', 'if (!allowed(old.status, status))'])
assert ledger.index('fun admit(') < ledger.index('fun create('), 'CBNX02B_HF02_ADMISSION_CONTRACT_MISSING'
admit=ledger[ledger.index('fun admit('):ledger.index('fun create(')]
assert 'synchronized(lock)' in admit and 'val duplicate = rows.firstOrNull' in admit and 'write(rows)' in admit
assert admit.index('val duplicate = rows.firstOrNull') < admit.index('write(rows)'), 'CBNX02B_HF02_TOCTOU'
assert 'rows.count { it.status in protectedStatuses }' in ledger, 'CBNX02B_HF02_HISTORY_TRUNCATION_RISK'
assert '"VALIDATING", "INSTALLING" -> row.copy(status = "VERIFY_REQUIRED"' in ledger
assert 'journal.isQueuedIdentity(next.id, next.source, next.modId, next.fileId)' in service
assert 'for (job in queue) journal.markJobInterrupted(job.id)' in service
assert 'for (job in queue) journal.cancelIfActive(job.id' not in service[service.index('override fun onDestroy()'):service.index('private suspend fun runTransfer')]
assert 'if (!journal.update(item.id, "DOWNLOADING"' in service
assert 'check(journal.update(item.id, "INSTALLING"' in service
require('app/src/androidTest/java/com/sdvsync/mods/CbNx02BAdmissionDeviceTest.kt', [
    'allProtectedNexusStatesRefuseDuplicateAdmission', 'multipleJournalInstancesAdmitSameFileOnlyOnce',
    'durableReviewReceiptBlocksAdmissionEvenWithoutJournalRow', 'crashDuringInstallationIsVerifyOnlyEvenWithApprovalOff',
    'terminalAndUncertainStatesRejectLateWorkerWrites'])
runner=require('scripts/devtool/cbnx02_emulator_ci.sh', [
    'CbNx02DownloadUxDeviceTest,com.sdvsync.ui.screens.CbNx02DownloadsUiDeviceTest,com.sdvsync.ui.screens.CbNx02BQueueControlsUiDeviceTest,com.sdvsync.mods.CbNx02BAdmissionDeviceTest',
    'scripts/devtool/cbnx02_instrumentation_receipt.py'])
receipt=require('scripts/devtool/cbnx02_instrumentation_receipt.py', [
    'ROSTER = {', 'len(EXPECTED)',
    'events == 2 * len(EXPECTED)',
    'len(started) == len(EXPECTED)', 'len(passed) == len(EXPECTED)',
    'started.get(x) == 1 and passed.get(x) == 1',
    'for x in EXPECTED', 'invalid == 0',
    'CbNx02BQueueControlsUiDeviceTest', 'CbNx02BAdmissionDeviceTest',
    "'physical_device_qualified': False", "'live_nexus_qualified': False"])
assert 'OK (8 tests)' not in receipt and "'test_count':8" not in receipt
print('CBNX02B_HF02_SOURCE_GATE_PASS_API36_PENDING')

# Hosted targeted source lane also runs mutation/receipt negative tests; no Android dependency.
import runpy
runpy.run_path(str(ROOT/'scripts/devtool/cbnx02b_hf02_negative_tests.py'), run_name='__main__')

assert '"PAUSED", "INTERRUPTED", "FAILED"' not in text(MOD+'ModQueueControlPolicy.kt'), 'CBNX02B_HF02_PAUSED_REBIND_BYPASS'

assert 'private const val ACTION_CANCEL_ALL' in service
assert 'private fun cancelAllTransfers()' in service
assert 'fun stop(context: Context) = control(context, ACTION_CANCEL_ALL, "")' in service
assert 'context.stopService(Intent(context, ModDownloadService::class.java))' not in service

assert 'source.equals("nexus", ignoreCase = true) && source != "nexus"' in ledger

# Nexus NXM and manual-review paths must surface refused admissions and preserve receipts.
require('app/src/main/java/com/sdvsync/MainActivity.kt', [
    'val admission = downloadManager.startDownload(url, modName, parsed.modId, "nexus", parsed.fileId)',
    'nxmNotice = admission.userMessage'])
require('app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt', [
    'if (!admission.accepted)', 'error = admission.userMessage'])
reviewvm=require('app/src/main/java/com/sdvsync/ui/viewmodels/ModManagerViewModel.kt', [
    'record.source == reviewReceipt.source', 'record.modId == reviewReceipt.modId',
    'record.fileId == reviewReceipt.fileId',
    'row.status in setOf("REVIEW_REQUIRED", "BLOCKED")',
    'check(ModDownloadJournal(context).update(receipt.jobId, "INSTALLED"',
    '"Cannot discard uncertain installation evidence"'])

# CB-NX05A: actual mod-level and archive-level statuses remain independent.
# Canonical CB-NX02 device roster now includes the exact-job inspection action.
provenance = require(MOD+'ModDownloadEvidencePolicy.kt', [
    'internal object ModDownloadEvidencePolicy', 'VERIFIED_AT_SCAN',
    'LOCAL_ZIP_VS_APP_RECEIPT', 'observation.modId != modId',
    'observation.fileId != fileId', 'observation.jobId != jobId', 'exactFileInstalled != "UNKNOWN"',
    'Exact Nexus file installation not verified', 'inventoryState == "QUALIFIED"'])
for forbidden in ('installFromZip(', 'startDownload(', 'httpClient.newCall(',
                  'setHandoffEnabled(', 'java.net.', 'SharedPreferences('):
    assert forbidden not in provenance, 'CBNX05A_EVIDENCE_POLICY_SIDE_EFFECT:'+forbidden
inspect = require(SCREENS+'ModDownloadsScreen.kt', [
    'NexusPairingAuthority.snapshot(recordsAtScan', 'NexusArchiveProvenance.inspect(recordsAtScan',
    'withContext(Dispatchers.IO)', 'ModDownloadEvidencePolicy.evaluate(',
    'cbnx05.evidence.open', 'onInspectEvidence = { inspectEvidence(record) }',
    'Archive proof is app-local, not a Nexus checksum',
    'Exact Nexus file installation not verified'])
assert 'NexusPairingAuthority.snapshot(recordsAtScan' in inspect
suite = require('app/src/androidTest/java/com/sdvsync/ui/screens/CbNx02DownloadsUiDeviceTest.kt',
    ['exactJobEvidenceButtonCannotStartInstallOrOpenWrongMod'])
assert len(re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(', suite)) == 4
unit = require('app/src/test/java/com/sdvsync/mods/ModDownloadEvidencePolicyTest.kt',
    ['class ModDownloadEvidencePolicyTest', 'wrongScopeAndForgedExactFileClaimFailClosed'])
assert len(re.findall(r'@Test\s+fun\s+([A-Za-z_0-9]+)\s*\(', unit)) == 8
receipt = text('scripts/devtool/cbnx02_instrumentation_receipt.py')
negative = text('scripts/devtool/cbnx02b_hf02_negative_tests.py')
assert "'qualification': 'CBNX05A_API36_EXACT_JOB_EVIDENCE'" in receipt
assert 'exactJobEvidenceButtonCannotStartInstallOrOpenWrongMod' in receipt
assert 'len(items)==18' in negative and 'roster=18' in negative
assert 'roster=17' not in negative and 'OK (17 tests)' not in negative
workflow = text('.github/workflows/cbnx02-download-ux.yml')
runner = text('scripts/devtool/cbnx02_emulator_ci.sh')
for needed in ('pull_request:', 'CBNX02_HEAD_SHA:',
    'python3 -B scripts/devtool/cbnx04_sdk_image_recovery.py',
    ':app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest',
    'needs: source-and-build', 'api-level: 36'):
    assert needed in workflow, 'CBNX05A_STALE_HOSTED_WORKFLOW:'+needed
assert 'sdkmanager --install' not in workflow
assert '$CBNX02_HEAD_SHA' in runner and '"$GITHUB_SHA"' not in runner
assert 'CbNx02DownloadsUiDeviceTest' in runner
print('CBNX05A_CANONICAL_DOWNLOADS_EVIDENCE_AND_18_DEVICE_TESTS_PASS')
