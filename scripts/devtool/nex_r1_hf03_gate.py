#!/usr/bin/env python3
"""HF03 read-only regression audit: semantics, screenshot liveness and evidence."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
UX='app/src/androidTest/java/com/sdvsync/ui/ux/UxReferenceParityTest.kt'
NEX='app/src/androidTest/java/com/sdvsync/ui/ux/NexR1NativeFiltersTest.kt'
RUN='scripts/devtool/nex_r1_emulator_ci.sh'
WORK='.github/workflows/cinderbox-nex-r1-native-catalog.yml'

def read(path,root=ROOT):
    p=root/path
    assert p.is_file() and not p.is_symlink(), 'HF03_MISSING_OR_LINKED:'+path
    return p.read_text(encoding='utf-8')

def check(ux,nex,runner,workflow):
    assert 'rule.onNodeWithTag("nex.r1.filter.apply").performScrollTo().performClick()' in ux, 'HF03_STALE_FILTER_ACTION'
    assert 'rule.onNodeWithText("Show results")' not in ux, 'HF03_OBSOLETE_BUTTON_LABEL'
    assert ux.count('@Test fun ')==9, 'HF03_UX09A_NINE_TESTS_LOST'
    assert 'rule.onNodeWithText("Refine discovery").assertDoesNotExist()' in ux, 'HF03_SHEET_CLOSE_PROOF_LOST'
    assert nex.count('@Test fun ')==1, 'HF03_NEX_ONE_TEST_LOST'
    assert 'nex.r1.filter.apply' in nex and 'nex.r1.filter.sheet' in nex, 'HF03_NATIVE_NAVIGATION_PROOF_LOST'
    assert 'step 41' not in nex and 'step 12' in nex, 'HF03_SPARSE_SAMPLER_REINTRODUCED'
    assert 'img.height / 8 until img.height * 7 / 8' in nex and 'img.width / 8 until img.width * 7 / 8' in nex, 'HF03_FULL_FRAME_SAMPLING'
    for guard in ('colors.size >= 8', 'backgroundPixels >= 64', 'foregroundPixels >= 5', 'foregroundRows >= 2'):
        assert guard in nex, 'HF03_MISSING_NONBLANK_GUARD:'+guard
    assert nex.index('ctx.openFileOutput(path') < nex.index('val colors = HashSet<Int>()'), 'HF03_CAPTURE_NOT_RETAINED_BEFORE_CHECK'
    assert 'Refuse blank or flat-content capture' in nex, 'HF03_NO_FAIL_CLOSED_CHECK'
    assert runner.count('for stage in mods filter; do') == 2, 'HF03_FAILURE_EVIDENCE_NOT_ALLOWLISTED'
    assert '2>/dev/null || rm -f -- "$out/$name"' in runner, 'HF03_EVIDENCE_RETRY_NOT_SAFE'
    assert 'grep -F \'OK (1 test)\'' in runner, 'HF03_NEX_EXACT_COUNT_LOST'
    assert "'test_nex_r1_hf03_gate.py' -v" in workflow, 'HF03_CI_SOURCE_GATE_MISSING'
    assert "source-contract" in workflow and "hosted-api36-real-native-filters" in workflow, 'HF03_HOSTED_CI_LOST'
    for forbidden in ('startDownload(', 'installMod(', 'toggleMod(', 'applyProfile(', 'requestShizukuPermission(', 'Runtime.getRuntime()'):
        assert forbidden not in nex, 'HF03_UNSAFE_TEST_ACTION:'+forbidden
    return {'old_ui_test_count':9,'new_ui_test_count':1,'screenshots_on_failure':'allowlisted_only','native_ui_changes':False,'real_emulator_run_required':True}

def run(root=ROOT):return check(*(read(p,root) for p in (UX,NEX,RUN,WORK)))
if __name__=='__main__':print('NEX_R1_HF03_SOURCE_PASS',run())
