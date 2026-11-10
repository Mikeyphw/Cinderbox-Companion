#!/usr/bin/env python3
"""CB-NX03B local negative contracts: reject mutations that reopen install/identity races.
Android/Firefox functional proof is in independently hosted tests.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GATE = 'scripts/devtool/cbnx03b_source_gate.py'
BRIDGE = 'app/src/main/java/com/sdvsync/mods/NexusPairingBridge.kt'
INBOX = 'app/src/main/java/com/sdvsync/mods/NexusPairingInbox.kt'
PANEL = 'app/src/main/java/com/sdvsync/ui/screens/NexusPairingPanel.kt'
PRIVACY = 'app/src/main/java/com/sdvsync/mods/NexusCompanionPrivacyPolicy.kt'
PRIVACY_TEST = 'app/src/test/java/com/sdvsync/mods/NexusCompanionPrivacyPolicyTest.kt'
DOWNLOADS = 'app/src/main/java/com/sdvsync/ui/screens/ModDownloadsScreen.kt'
RECEIPT = 'scripts/devtool/cbnx03_instrumentation_receipt.py'
TEST = 'app/src/androidTest/java/com/sdvsync/mods/CbNx03PairingDeviceTest.kt'
FILES = [GATE, BRIDGE, INBOX, PANEL, DOWNLOADS, PRIVACY, PRIVACY_TEST, RECEIPT, TEST,
         'scripts/devtool/cbnx03_hf01_negative_tests.py',
         'scripts/devtool/cbnx03_emulator_ci.sh', '.github/workflows/cbnx03-pairing.yml']

with TemporaryDirectory(prefix='cbnx03b-negative-') as tmp:
    fake = Path(tmp)
    for name in FILES:
        target = fake / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    def run():
        return subprocess.run([sys.executable, '-B', str(fake / GATE)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=12)
    baseline = run()
    assert baseline.returncode == 0, 'CBNX03B_NEGATIVE_BASELINE_INVALID:' + baseline.stderr[-300:]
    cases = [
        (BRIDGE, 'private var permitHandoffs = false', 'private var permitHandoffs = true'),
        (BRIDGE, 'if (!permitHandoffs)', 'if (false)'),
        (BRIDGE, '.put("download_started", false)', '.put("download_started", true)'),
        (BRIDGE, 'NexusPairingInbox.admit(context, id, mod, file)', 'null'),
        (INBOX, 'fun initializeForLocalPairing(context: Context): Boolean = synchronized(lock)',
            'fun initializeForLocalPairing(context: Context): Boolean = synchronized(Any())'),
        (INBOX, 'fun verifiedHistory(context: Context): List<Entry> = synchronized(lock)',
            'fun verifiedHistory(context: Context): List<Entry> = synchronized(Any())'),
        (INBOX, 'fun list(context: Context): List<Entry> = synchronized(lock)',
            'fun list(context: Context): List<Entry> = synchronized(Any())'),
        (INBOX, 'fun admit(context: Context, id: String, modId: String, fileId: String): Admission = synchronized(lock)',
            'fun admit(context: Context, id: String, modId: String, fileId: String): Admission = synchronized(Any())'),
        (INBOX, 'fun resolve(context: Context, id: String, status: String): Boolean = synchronized(lock)',
            'fun resolve(context: Context, id: String, status: String): Boolean = synchronized(Any())'),
        (INBOX, 'Regex("[1-9][0-9]{0,11}")', 'Regex("[0-9]{1,12}")'),
        (INBOX, '.commit()', '.apply()'),
        (INBOX, 'private const val MAX_PENDING = 8', 'private const val MAX_PENDING = 1000'),
        (PANEL, 'NexusBrowserHandoff.createUrl(item.modId, item.fileId)', '"https://example.com/"'),
        (RECEIPT, "'test_count': 7 if ok else 0", "'test_count': 4 if ok else 0"),
        (DOWNLOADS, 'cbnx05b.downloads.companion', 'cbnx05b.downloads.stale'),
        (PRIVACY, 'check(json.length <= 4096)', 'check(json.length <= 100000)'),
        (PRIVACY, 'if (inboxAvailable) "{${counts(requests, history.take(40))}}" else "null"',
            '"{${counts(requests, history.take(40))}}"'),
        (PRIVACY, 'if (journalAvailable) "{${counts(jobs, statuses.take(60))}}" else "null"',
            '"{${counts(jobs, statuses.take(60))}}"'),
        (PRIVACY, 'fun redactedId(value: String)', 'fun unsafeId(value: String)'),
        (PANEL, 'val loaded = runCatching { NexusPairingInbox.verifiedHistory(context) }',
            'val loaded = runCatching { NexusPairingInbox.list(context) }'),
        (PANEL, 'Intent.createChooser(share', 'share.also(share'),
        (INBOX, 'if (prefs.getBoolean(EVER_INITIALIZED, false)) {\n            check(prefs.contains(KEY))',
            'if (prefs.getBoolean(EVER_INITIALIZED, false)) {\n            check(true)'),
        (INBOX, 'fun verifiedHistory(context: Context): List<Entry> = synchronized(lock) {\n        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n        check(prefs.contains(KEY))',
            'fun verifiedHistory(context: Context): List<Entry> = synchronized(lock) {\n        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n        check(true)'),
        (INBOX, '.putBoolean(EVER_INITIALIZED, true)', '.putBoolean(EVER_INITIALIZED, false)'),
        (BRIDGE, 'NexusPairingInbox.initializeForLocalPairing(context)', 'true'),
        (PRIVACY_TEST, '@Test fun untrustedFieldsCannotBeExported()',
            'fun untrustedFieldsCannotBeExported()'),
        (TEST, '@Test fun inboxSurvivesBridgeShutdownWithoutReenqueuingAnything()',
            'fun inboxSurvivesBridgeShutdownWithoutReenqueuingAnything()'),
    ]
    for name, before, after in cases:
        file = fake / name
        original = file.read_text(encoding='utf8')
        assert before in original, 'CBNX03B_MUTATION_ANCHOR_STALE:' + before
        file.write_text(original.replace(before, after, 1), encoding='utf8')
        mutated = run()
        assert mutated.returncode != 0, 'CBNX03B_NEGATIVE_ESCAPED:' + name + ':' + before
        file.write_text(original, encoding='utf8')
print('CBNX03B_OFFLINE_SECURITY_NEGATIVES_PASS mutations=27')
