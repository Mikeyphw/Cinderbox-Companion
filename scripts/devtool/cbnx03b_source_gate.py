#!/usr/bin/env python3
"""CB-NX03B source/security contract; fails on stale emulator roster and lost local consent.

Not equivalent to a real browser or device test.
"""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def source(path):
    file = ROOT / path
    assert file.is_file() and not file.is_symlink(), 'CBNX03B_MISSING:' + path
    return file.read_text(encoding='utf8')

mods = 'app/src/main/java/com/sdvsync/mods/'
bridge = source(mods + 'NexusPairingBridge.kt')
inbox = source(mods + 'NexusPairingInbox.kt')
panel = source('app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt')
downloads = source('app/src/main/java/com/sdvsync/ui/screens/ModDownloadsScreen.kt')
privacy = source(mods + 'NexusCompanionPrivacyPolicy.kt')
privacy_tests = source('app/src/test/java/com/sdvsync/mods/NexusCompanionPrivacyPolicyTest.kt')
tests = source('app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt')
receipt = source('scripts/devtool/cbnx03_instrumentation_receipt.py')
negative = source('scripts/devtool/cbnx03_hf01_negative_tests.py')
runner = source('scripts/devtool/cbnx03_emulator_ci.sh')
workflow = source('.github/workflows/cbnx03-pairing.yml')
for key in ('private var permitHandoffs = false', 'fun setHandoffEnabled(enabled: Boolean)',
            'method == "POST" && path == "/v1/handoff"',
            'if (!permitHandoffs)', 'NexusPairingInbox.admit(context, id, mod, file)',
            '.put("download_started", false)', '.put("archive_staged", false)',
            '.put("installed", false)', 'NexusPairingInbox.list(context)',
            'inbox_available', 'method == "POST" && path == "/v1/revoke"',
            'MessageDigest.isEqual', 'x-cbnx-nonce',
            'bind(InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 4)'):
    assert key in bridge, 'CBNX03B_BRIDGE_CONTRACT:' + key
for key in ('private const val MAX_PENDING = 8', 'private const val MAX_HISTORY = 32',
            'Regex("[1-9][0-9]{0,11}")', 'Regex("[A-Za-z0-9_-]{22,64}")',
            'fun admit(', 'fun resolve(', 'synchronized(lock)', '.commit()',
            'it.status == "PENDING"', 'already_pending', 'identity_conflict',
            'inbox_full', 'already_seen', '"OPENED"', '"DISMISSED"'):
    assert key in inbox, 'CBNX03B_INBOX_CONTRACT:' + key
# CB-NX05B HF01: each public storage entrypoint MUST use the same shared lock.
# A global count was unsafe: mutating one lock escaped while others remained.
critical_locks = (
    'fun initializeForLocalPairing(context: Context): Boolean = synchronized(lock)',
    'fun verifiedHistory(context: Context): List<Entry> = synchronized(lock)',
    'fun list(context: Context): List<Entry> = synchronized(lock)',
    'fun admit(context: Context, id: String, modId: String, fileId: String): Admission = synchronized(lock)',
    'fun resolve(context: Context, id: String, status: String): Boolean = synchronized(lock)',
)
for declaration in critical_locks:
    assert inbox.count(declaration) == 1, 'CBNX05B_HF01_LOCK_BOUNDARY_BROKEN:' + declaration
# Both corruption guards are necessary. The history guard must never mask
# removal of the persistent read() initialization guard.
read_guard = 'if (prefs.getBoolean(EVER_INITIALIZED, false)) {\n            check(prefs.contains(KEY))'
assert read_guard in inbox, 'CBNX05B_HF01_READ_GUARD_BROKEN'
history_guard = 'fun verifiedHistory(context: Context): List<Entry> = synchronized(lock) {\n        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n        check(prefs.contains(KEY))'
assert history_guard in inbox, 'CBNX05B_HF01_HISTORY_GUARD_BROKEN'
for forbidden in ('startDownload(', 'installFromZip(', 'ModDownloadService(',
                  'getDownloadUrl(', 'getSharedPreferences("nexus', '0.0.0.0',
                  'android.permission.QUERY_ALL_PACKAGES'):
    assert forbidden not in bridge + inbox, 'CBNX03B_PRIVILEGED_CAPABILITY:' + forbidden
for forbidden in ('download_url', 'session_cookie', 'nexus_key', 'nxm://'):
    assert forbidden not in inbox, 'CBNX03B_PERSISTENCE_PRIVACY:' + forbidden
assert 'NexusPairingBridge.setHandoffEnabled(it)' in panel
assert 'NexusPairingInbox.resolve(context, item.id, "OPENED")' in panel
assert 'NexusPairingInbox.resolve(context, item.id, "DISMISSED")' in panel
assert 'NexusBrowserHandoff.createUrl(item.modId, item.fileId)' in panel
assert 'cbnx03b.handoff.open-exact' in panel
assert panel.index('NexusBrowserLauncher.open(context, url)') < panel.index('NexusPairingInbox.resolve(context, item.id, "OPENED")')
# Setter is a UI-only function; HTTP may not invoke it. Gate the entire route on current user approval.
assert bridge.index('if (!permitHandoffs)') < bridge.index('NexusPairingInbox.admit(context, id, mod, file)')
assert 'CbNx03PairingDeviceTest' in runner and 'api-level: 36' in workflow
assert 'cbnx03b_source_gate.py' in workflow and 'cbnx03b_negative_tests.py' in workflow
methods = tuple(re.findall(r'@Test\s+fun\s+([A-Za-z0-9_]+)\(', tests))
assert len(methods) == 7 and len(set(methods)) == 7, 'CBNX03B_DEVICE_TEST_COUNT_DRIFT'
for name in methods:
    assert name in receipt and name in negative, 'CBNX03B_METHOD_MISSING:' + name
assert 'method_events != 14' in receipt and "'test_count': 7 if ok else 0" in receipt
assert "'OK (7 tests)'" in receipt and "block.get('numtests') != '7'" in receipt
assert 'numtests: int = len(METHODS)' in negative and "data['event_count'] == 14" in negative
# CB-NX05B migrated in-place: retain the canonical seven device methods, and
# additionally require the new JVM privacy tests and explicit safe sharing UX.
for marker in ('fun verifiedHistory(context: Context)', 'check(prefs.contains(KEY))',
               'read(context).filter', 'HISTORY_MS',
               'EVER_INITIALIZED', 'putBoolean(EVER_INITIALIZED, true)',
               'fun initializeForLocalPairing(context: Context)'):
    assert marker in inbox, 'CBNX05B_VERIFIED_HISTORY_DRIFT:' + marker
assert 'NexusPairingInbox.initializeForLocalPairing(context)' in bridge
for marker in ('val loaded = runCatching { NexusPairingInbox.verifiedHistory(context) }',
               'inbox = loaded.getOrDefault(emptyList())',
               'cbnx05b.handoff.history', 'NexusCompanionPrivacyPolicy.redactedId(item.modId)',
               'NexusCompanionPrivacyPolicy.redactedId(item.fileId)',
               'Opened is not downloaded', 'cbnx05b.diagnostics.preview',
               'cbnx05b.diagnostics.redacted', 'cbnx05b.diagnostics.share',
               'Intent.createChooser(share', 'journalResult.isSuccess'):
    assert marker in panel, 'CBNX05B_NATIVE_UX_DRIFT:' + marker
for marker in ('cbnx05b.downloads.companion', 'NexusPairingBridge.snapshot()',
               'Pair or revoke in Settings. Choose a download destination in Firefox.'):
    assert marker in downloads, 'CBNX05B_DOWNLOADS_INTEGRATION_STALE:' + marker
for marker in ('fun redactedId(value: String)', 'fun report(appVersion:',
               'private val safeVersion', 'fun isKnownJobStatus(value: String)',
               'if (inboxAvailable) "{${counts(requests, history.take(40))}}" else "null"',
               'if (journalAvailable) "{${counts(jobs, statuses.take(60))}}" else "null"',
               'check(json.length <= 4096)', '"VERIFY_REQUIRED"', '"INSTALLED"'):
    assert marker in privacy, 'CBNX05B_PRIVACY_CONTRACT_DRIFT:' + marker
for forbidden in ('Throwable.message', '.stackTraceToString()', 'Log.d(', 'Log.e(',
                  'nxm://', 'getDownloadUrl(', 'Authorization', 'android.permission.'):
    assert forbidden not in privacy + panel, 'CBNX05B_DIAGNOSTIC_LEAK:' + forbidden
methods = re.findall(r'@Test\s+fun\s+(\w+)\s*\(', privacy_tests)
assert len(methods) == 5 and len(set(methods)) == 5, 'CBNX05B_JVM_TEST_ROSTER_STALE'
for name in ('masksExactIdentitiesWithoutGuessingInvalidOnes',
             'reportContainsOnlyFixedEnumsAndCounts', 'untrustedFieldsCannotBeExported',
             'corruptOrUnknownHistoryMustNotBeRepresentedAsVerifiedZero',
             'onlyWhitelistedJobStatesAreCounted'):
    assert name in methods, 'CBNX05B_MISSING_PRIVACY_TEST:' + name
for required_path in ('NexusCompanionPrivacyPolicy.kt', 'NexusCompanionPrivacyPolicyTest.kt',
                      'cbnx03b_source_gate.py', 'cbnx03b_negative_tests.py'):
    assert required_path in workflow, 'CBNX05B_WORKFLOW_TRIGGER_STALE:' + required_path
print('CBNX03B_SOURCE_AND_ROSTER_PASS test_count=7 no_install_capabilities=true')
print('CBNX05B_NATIVE_INTEGRATION_AND_REDACTED_DIAGNOSTICS_CONTRACT_PASS tests=5')
