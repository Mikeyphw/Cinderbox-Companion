#!/usr/bin/env python3
"""NEX-R3 HF02: status-backed LazyColumn error verification, fail closed."""
from __future__ import annotations
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
TEST='app/src/androidTest/java/com/sdvsync/ui/ux/NexR3NativeJourneyTest.kt'
RUNNER='scripts/devtool/nex_r3_emulator_ci.sh'
WORKFLOW='.github/workflows/nex-r3-real-native-journey.yml'
DOC='docs/devtool/NEX_R3_HF02_STATUS_BACKED_ERRORS.md'
POLICY='docs/security/M3_RELEASE_POLICY.json'

def check(root: Path=ROOT)->list[str]:
    root=Path(root)
    def read(rel):
        p=root/rel
        if not p.is_file() or p.is_symlink(): raise ValueError('NEX_R3_HF02_MISSING_OR_SYMLINK:'+rel)
        return p.read_text(encoding='utf-8')
    test=read(TEST);run=read(RUNNER);wf=read(WORKFLOW);doc=read(DOC)
    policy=json.loads(read(POLICY))
    required={
      'status recording': 'responseCodes = Collections.synchronizedList' in test and
        'responseCodes.add(code)' in test,
      'status-backed error UI': all(x in test for x in ('private fun expectCatalogHttpFailure(',
        'compose.waitUntil(35000L) { transport.responseCodes.contains(status) }',
        '.performScrollToNode(androidx.compose.ui.test.hasText("Mod catalog unavailable"))',
        'compose.onNodeWithText("Mod catalog unavailable").assertIsDisplayed()',
        'NEX_R3_HTTP_ERROR_TIMEOUT:', 'NEX_R3_HTTP_ERROR_UI_TIMEOUT:')),
      'all 3 scenarios': all(x in test for x in ('expectCatalogHttpFailure(401, "auth-401")',
        'expectCatalogHttpFailure(429, "rate-429")','expectCatalogHttpFailure(503, "server-503")',
        'capture("auth-401")','capture("rate-429")','capture("server-503")')),
      'real journey and no-key unaffected': all(x in test for x in (
        'realMainActivityDiscoverPagingDetailReviewAndBack','noNexusKeyKeepsLocalModsRouteAvailable',
        'assertNoDownloadRequests()', 'RuleChain.outerRule(fixture).around(compose)',
        'NEX_R3_REFUSED_NON_EPHEMERAL_DEVICE')),
      'per-viewport ephemerality': all(x in run for x in (
        'for width in 393 360; do', 'ro.kernel.qemu',
        'r48_offline_gate.py', 'pm clear com.sdvsync',
        'NEX_R3_EPHEMERAL_APP_DATA_RESET_REFUSED')) and
        run.index('pm clear com.sdvsync') > run.index('for width in 393 360; do') >
        run.index('r48_offline_gate.py'),
      'offline runner': all(x in run for x in ('r48_offline_gate.py','font_scale 1.0',
        'NEX_R3_HOSTED_INSTRUMENTATION_REFUSED','NEX_R3_SANITIZED_FAILURE_DIAGNOSTIC',
        'NexR3NativeJourneyTest','OK (3 tests)')),
      'bounded coded diagnostics': run.count('HTTP_ERROR|HTTP_ERROR_UI') == 2 and
        r'[a-z0-9_:=\-]+' in run and 'SECRET' not in run,
      'source gate hosted': all(x in wf for x in ('nex_r3_hf02_gate.py',
        'test_nex_r3_hf02_gate.py','nex_r3_hf01_gate.py',
        'assembleDebugAndroidTest', 'android-emulator-runner@')),
      'evidence honesty': all(x in doc.lower() for x in ('synthetic', 'not live nexus',
        '429', 'scroll', 'not release approval')),
    }
    errors=['NEX_R3_HF02_MISSING:'+k for k,ok in required.items() if not ok]
    for x in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        if policy.get(x) is not False:errors.append('NEX_R3_HF02_RELEASE_DRIFT:'+x)
    for forbidden in ('CINDERBOX_NEXUS_API_KEY','getDownloadUrl(', 'startDownload(',
      'installFile(', 'requestShizukuPermission(', 'WebView(', 'Runtime.getRuntime('):
        if forbidden in test+run+wf:errors.append('NEX_R3_HF02_UNSAFE:'+forbidden)
    return errors

if __name__=='__main__':
    try:errors=check()
    except (ValueError,OSError,KeyError,TypeError) as e:raise SystemExit('NEX_R3_HF02_REFUSED:'+str(e))
    if errors:raise SystemExit('\n'.join(errors))
    print('NEX_R3_HF02_STATUS_BACKED_LAZY_ERROR_SOURCE_PASS')
