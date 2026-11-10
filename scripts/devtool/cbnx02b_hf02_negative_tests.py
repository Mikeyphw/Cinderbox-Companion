#!/usr/bin/env python3
"""Offline source/receipt mutation tests. No Android, GitHub credentials, or Gradle."""
import importlib.util
import hashlib
from pathlib import Path
import sys

ROOT = (Path(__file__).resolve().parent if (Path(__file__).resolve().parent/'app').is_dir()
        else Path(__file__).resolve().parents[2])


def load_receipt():
    spec = importlib.util.spec_from_file_location('receipt', ROOT/'scripts/devtool/cbnx02_instrumentation_receipt.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_source():
    mgr=(ROOT/'app/src/main/java/com/sdvsync/mods/ModDownloadManager.kt').read_text()
    ledger=(ROOT/'app/src/main/java/com/sdvsync/mods/ModDownloadJournal.kt').read_text()
    svc=(ROOT/'app/src/main/java/com/sdvsync/mods/ModDownloadService.kt').read_text()
    gate=(ROOT/'scripts/devtool/cbnx02_source_gate.py').read_text()
    runner=(ROOT/'scripts/devtool/cbnx02_emulator_ci.sh').read_text()
    for state in ('PAUSED', 'VERIFY_REQUIRED', 'REVIEW_REQUIRED', 'BLOCKED'):
        assert f'"{state}"' in ledger[ledger.index('private val protectedStatuses'):ledger.index('private val known')], state
    method=ledger[ledger.index('fun admit('):ledger.index('fun create(')]
    assert 'synchronized(lock)' in method
    assert method.index('val duplicate = rows.firstOrNull') < method.index('write(rows)')
    assert 'journal.admit(' in mgr and 'journal.list().any' not in mgr
    assert 'if (!allowed(old.status, status))' in ledger
    assert '"VERIFY_REQUIRED", "INSTALLED", "COMPLETED"' in ledger
    assert 'rows.filter { it.status in protectedStatuses }' in ledger
    assert 'hasUnresolvedReviewIdentity(' in ledger
    assert 'source.equals("nexus", ignoreCase = true)' in ledger
    assert 'isQueuedIdentity(next.id, next.source, next.modId, next.fileId)' in svc
    assert 'for (job in queue) journal.markJobInterrupted(job.id)' in svc
    assert 'private fun cancelAllTransfers()' in svc
    assert 'fun stop(context: Context) = control(context, ACTION_CANCEL_ALL, "")' in svc
    assert 'for (job in queue) journal.cancelIfActive(job.id' not in svc[svc.index('override fun onDestroy()'):svc.index('private suspend fun runTransfer')]
    assert 'journal.update(item.id, "VERIFY_REQUIRED"' in svc or 'if (uncertain) "VERIFY_REQUIRED"' in svc
    assert 'check(journal.update(item.id, "INSTALLING"' in svc
    assert 'check(journal.update(item.id, "INSTALLED"' in svc
    assert 'CbNx02BAdmissionDeviceTest' in runner and 'CbNx02BQueueControlsUiDeviceTest' in runner
    assert 'CBNX02B_HF02_SOURCE_GATE_PASS' in gate
    for s in ('url','token','cookie','expires','key','nxm','downloadUrl'):
        assert f'.put("{s}"' not in ledger and f'setProperty("{s}"' not in ledger
    return mgr, ledger, svc, runner


def mutate_negative_tests(manager, ledger, service, runner):
    def atomic_check(s):
        method=s[s.index('fun admit('):s.index('fun create(')]
        return 'synchronized(lock)' in method and method.index('val duplicate = rows.firstOrNull') < method.index('write(rows)')
    assert atomic_check(ledger)
    assert not atomic_check(ledger.replace('fun admit(name: String, source: String, modId: String, fileId: String): ModDownloadAdmission = synchronized(lock) {',
        'fun admit(name: String, source: String, modId: String, fileId: String): ModDownloadAdmission = run {'))
    states=ledger[ledger.index('private val protectedStatuses'):ledger.index('private val known')]
    for token in ('"PAUSED"','"VERIFY_REQUIRED"','"REVIEW_REQUIRED"','"BLOCKED"'):
        assert token in states
        assert token not in states.replace(token,'"REMOVED_MUTATION"')
    assert 'CbNx02BQueueControlsUiDeviceTest' in runner
    assert 'CbNx02BQueueControlsUiDeviceTest' not in runner.replace('CbNx02BQueueControlsUiDeviceTest','RemovedTest')
    assert 'if (!allowed(old.status, status))' in ledger
    assert 'if (!allowed(old.status, status))' not in ledger.replace('if (!allowed(old.status, status))', 'if (false)')
    assert 'if (uncertain) "VERIFY_REQUIRED"' in service
    assert 'if (uncertain) "VERIFY_REQUIRED"' not in service.replace('if (uncertain) "VERIFY_REQUIRED"','if (uncertain) "FAILED"')


def receipt_tests():
    mod=load_receipt()
    items=sorted(mod.EXPECTED)
    assert len(items)==17, len(items)
    raw=''.join(f'INSTRUMENTATION_STATUS: class={c}\nINSTRUMENTATION_STATUS: test={t}\nINSTRUMENTATION_STATUS_CODE: 1\nINSTRUMENTATION_STATUS: class={c}\nINSTRUMENTATION_STATUS: test={t}\nINSTRUMENTATION_STATUS_CODE: 0\n' for c,t in items)
    raw+='OK (17 tests)\n'
    src='a'*40; app='b'*64; apk='c'*64
    assert mod.validate(raw,0,src,app,app,apk)
    bad={
      'missing_class_or_test':raw.replace(f'INSTRUMENTATION_STATUS: class={items[0][0]}\nINSTRUMENTATION_STATUS: test={items[0][1]}\nINSTRUMENTATION_STATUS_CODE: 0\n','',1),
      'bad_legacy_count':raw.replace('OK (17 tests)','OK (8 tests)'),
      'bad_status':raw+'INSTRUMENTATION_FAILED\n',
      'duplicate_test':raw.replace('OK (17 tests)',f'INSTRUMENTATION_STATUS: class={items[0][0]}\nINSTRUMENTATION_STATUS: test={items[0][1]}\nINSTRUMENTATION_STATUS_CODE: 0\nOK (17 tests)'),
      'incorrect_roster':raw.replace(f'INSTRUMENTATION_STATUS: test={items[0][1]}', 'INSTRUMENTATION_STATUS: test=unrelated',2),
    }
    for label,value in bad.items(): assert not mod.validate(value,0,src,app,app,apk), label
    assert not mod.validate(raw,1,src,app,app,apk)
    assert not mod.validate(raw,0,src,app,'c'*64,apk)
    assert not mod.validate(raw,0,'x'*40,app,app,apk)
    # The receipt is intentionally only a closed roster, never a raw log copy.
    assert 'raw' not in str(mod.validate(raw,0,src,app,app,apk))
    return len(bad)+3


def main():
    mgr, journal, svc, runner=verify_source()
    mutate_negative_tests(mgr,journal,svc,runner)
    n=receipt_tests()
    print(f'CBNX02B_HF02_OFFLINE_NEGATIVE_PASS roster=17 receipt_mutations={n} source_mutations=8')

if __name__=='__main__': main()
