#!/usr/bin/env python3
"""A10 native-by-default + canonical reusable legacy workflow contracts.

Host-only, deterministic, no GitHub dispatch or Android device operations.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
DISPATCH='.github/workflows/devtool-android-build.yml'
LEGACY='.github/workflows/build.yml'
M3='scripts/devtool/m3_build_evidence.py'
LEGACY_SHA256='74f76490dea605b0ac07ae60ca2ccc053dd9f4e461ed1ecff5298351352b9a26'
A10_START='      # A10: keep the original Devtool legacy artifact contract only when'
A10_END='      - name: M23 synthetic Android test source contract\n'

sys.path.insert(0,str(ROOT/'scripts/devtool'))
import m3_build_evidence as m3
import a07_native_debug as a07


def files():
    return {p:(ROOT/p).read_text('utf-8') for p in (DISPATCH,LEGACY)}


def check_contract(root:Path=ROOT)->None:
    src=(root/DISPATCH).read_text('utf8')
    legacy=(root/LEGACY).read_text('utf8')
    # The only modification to the established source/Gradle/Android-test
    # fallback is to grant workflow_call access. Its original contents are frozen.
    if legacy.count('  workflow_call:\n')!=1:
        raise ValueError('Legacy reusable trigger is missing or ambiguous')
    frozen=legacy.replace('  workflow_call:\n','',1)
    if frozen.count(A10_START)!=1 or frozen.count(A10_END)!=1:
        raise ValueError('Original Devtool fallback artifact staging missing')
    frozen=frozen[:frozen.index(A10_START)]+frozen[frozen.index(A10_END):]
    frozen=frozen.encode()
    if hashlib.sha256(frozen).hexdigest()!=LEGACY_SHA256:
        raise ValueError('Legacy full CI body or source gates drifted')
    a=src.split('  build-debug-apk:\n')
    if len(a)!=2 or '  a07-native-debug-build:\n' not in a[1]:
        raise ValueError('Legacy or A07 job boundary missing')
    block=a[1].split('  a07-native-debug-build:\n')[0]
    want=("    if: ${{ inputs.a05_mode != 'native-only' }}\n"
          '    uses: ./.github/workflows/build.yml\n'
          '    permissions:\n'
          '      contents: read\n'
          '    secrets: inherit\n')
    if block.strip()!=want.strip():
        raise ValueError('Legacy fallback not a single guarded reusable workflow job')
    if src.count('uses: ./.github/workflows/build.yml')!=1:
        raise ValueError('Unexpected duplicate reusable legacy workflow')
    if ('default: true\n' not in src.split('      a07_native_build:',1)[1].split('      a05_mode:',1)[0]
          or "default: 'native-only'" not in src.split('      a05_mode:',1)[1].split('permissions:',1)[0]):
        raise ValueError('Native no longer the manual dispatch default')
    # Keep A05 and A07 mutually independent; a failed native operation must
    # never silently dispatch the old builder.
    if "if: ${{ inputs.a07_native_build == true && inputs.a05_mode == 'native-only' }}" not in src:
        raise ValueError('Native lane no longer restricted to native-only mode')
    if 'if: failure()' in block or 'if: always()' in block:
        raise ValueError('Legacy fallback must never auto-retry failed native')
    if '  workflow_call:\n' not in legacy or '  push:\n' not in legacy or '  pull_request:\n' not in legacy:
        raise ValueError('Push/PR legacy gates or reusable entry missing')
    if '    steps:\n' not in legacy or 'M16 verify pinned instrumentation APK signer' not in legacy:
        raise ValueError('Existing M3-M24 CI steps missing')
    # The canonical legacy job remains the old GitHub build and preserves its
    # established checks and artifact names.
    for required in ('m3_build_evidence.py source','m3_build_evidence.py generate',
                     'm13_qualification.py finalize','test_m24_gate.py',
                     'm16_debug_signing.py provision','m16_debug_signing.py verify',
                     ':app:assembleDebugAndroidTest','name: debug-apk',
                     'name: m14-androidtest-apk'):
        if required not in legacy:
            raise ValueError('Legacy fallback lost '+required)
    # Avoid replacing the independently accepted A07 verifier with self-report.
    a07.source_contract(root)
    m3.check_source(root)


class ConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix='cinderbox-a10-test-')
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        for f in (DISPATCH,LEGACY,'.devtool.toml','docs/security/M3_RELEASE_POLICY.json',
                  'app/src/main/AndroidManifest.xml','app/build.gradle.kts'):
            dst=self.root/f;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/f,dst)
    def write(self,name,old,new):
        path=self.root/name;s=path.read_text('utf8');self.assertIn(old,s)
        path.write_text(s.replace(old,new,1),'utf8')
    def test_delegated_source_is_bounded_and_frozen(self):
        from ci_workflow_contract import effective_ci_source, validated_legacy_and_dispatch
        legacy, manual=validated_legacy_and_dispatch(self.root)
        result=effective_ci_source(self.root,DISPATCH)
        self.assertIn('  a07-native-debug-build:',result)
        self.assertIn("-p 'test_m17_*.py'",result)
        self.assertEqual(result.count('M14 compile isolated Android instrumentation APK'),1)
        self.assertIn('name: devtool-android-debug-apk',result)
    def test_false_reusable_source_is_rejected_before_merging(self):
        from ci_workflow_contract import effective_ci_source
        self.write(DISPATCH,'uses: ./.github/workflows/build.yml','uses: attacker/repo@main')
        with self.assertRaisesRegex(ValueError,'A10_DELEGATED_LEGACY_JOB_DRIFT'):
            effective_ci_source(self.root,DISPATCH)
    def test_fallback_artifact_staging_is_source_bound(self):
        from ci_workflow_contract import validated_legacy_and_dispatch
        self.write(LEGACY,'name: devtool-android-debug-apk','name: unrelated-artifact')
        with self.assertRaisesRegex(ValueError,'A10_LEGACY_ARTIFACT_SHAPE_DRIFT'):
            validated_legacy_and_dispatch(self.root)
    def test_symlink_in_canonical_build_refused(self):
        from ci_workflow_contract import effective_ci_source
        dst=self.root/LEGACY
        body=dst.read_bytes()
        dst.unlink()
        outside=self.root/'outside.yml'
        outside.write_bytes(body)
        dst.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'A10_SYMLINK_SOURCE'):
            effective_ci_source(self.root,DISPATCH)

    def test_exact_default_and_existing_fallback(self):
        check_contract(self.root)
    def test_old_ci_body_is_exactly_preserved(self):
        s=(self.root/LEGACY).read_text()
        s=s.replace('  workflow_call:\n','',1)
        s=s[:s.index(A10_START)]+s[s.index(A10_END):]
        self.assertEqual(hashlib.sha256(s.encode()).hexdigest(),LEGACY_SHA256)
    def test_missing_reusable_trigger_refused(self):
        self.write(LEGACY,'  workflow_call:\n','')
        with self.assertRaisesRegex(ValueError,'trigger'):
            check_contract(self.root)
    def test_legacy_grants_no_extra_permissions(self):
        self.write(DISPATCH,'      contents: read\n    secrets: inherit','      contents: write\n    secrets: inherit')
        with self.assertRaisesRegex(ValueError,'single guarded'):
            check_contract(self.root)
    def test_missing_inherited_debug_signer_refused(self):
        self.write(DISPATCH,'    secrets: inherit\n','    secrets: {}\n')
        with self.assertRaisesRegex(ValueError,'single guarded'):
            check_contract(self.root)
    def test_legacy_fallback_preserves_original_devtool_artifact_format(self):
        flow=(self.root/LEGACY).read_text()
        block=flow.split(A10_START,1)[-1].split(A10_END,1)[0]
        for part in ("if: github.event_name == 'workflow_dispatch'",
                     'stage="$RUNNER_TEMP/cinderbox-devtool-debug"',
                     'sha256sum debug.apk > SHA256SUMS',
                     'BUILD_INFO.txt','M3_PROVENANCE.json','M13_QUALIFICATION.json',
                     'name: devtool-android-debug-apk','if-no-files-found: error'):
            self.assertIn(part,block)

    def test_no_duplicated_full_legacy_gradle_steps(self):
        s=(self.root/DISPATCH).read_text()
        # Legacy compile steps must exist only in reusable fallback, not in
        # either Devtool native job.
        self.assertNotIn('assembleDebugAndroidTest',s)
        self.assertIn('assembleDebugAndroidTest',(self.root/LEGACY).read_text())
        self.assertIn('name: devtool-android-debug-apk',(self.root/LEGACY).read_text())
    def test_removing_full_instrumentation_gate_refused(self):
        self.write(LEGACY,':app:assembleDebugAndroidTest',':app:testDebugUnitTest')
        with self.assertRaisesRegex(ValueError,'drifted'):
            check_contract(self.root)
    def test_wrong_default_to_legacy_refused(self):
        self.write(DISPATCH,"default: 'native-only'","default: 'off'")
        with self.assertRaises((ValueError,a07.Refused)):
            check_contract(self.root)
    def test_unintentional_dual_apk_path_refused(self):
        self.write(DISPATCH,"inputs.a05_mode != 'native-only'","inputs.a05_mode != 'off'")
        with self.assertRaisesRegex(ValueError,'single guarded'):
            check_contract(self.root)
    def test_wrong_fallback_target_refused(self):
        self.write(DISPATCH,'uses: ./.github/workflows/build.yml','uses: remote/unknown@main')
        with self.assertRaisesRegex(ValueError,'single guarded'):
            check_contract(self.root)
    def test_disable_native_without_changing_legacy_refused(self):
        self.write(DISPATCH,'default: true','default: false')
        with self.assertRaises((ValueError,a07.Refused)):
            check_contract(self.root)
    def test_release_claim_refused(self):
        path=self.root/LEGACY
        path.write_text(path.read_text()+'\n# assembleRelease\n')
        with self.assertRaisesRegex(ValueError,'drifted'):
            check_contract(self.root)
    def test_exact_source_only_a05_remains_available(self):
        flow=(self.root/DISPATCH).read_text()
        self.assertIn('  a05-native-devtool-dag:',flow)
        self.assertIn("if: ${{ inputs.a05_mode == 'native-only' || inputs.a05_mode == 'both' }}",flow)
        self.assertIn('m24-verify-ux-check',flow)
    def test_fallback_is_not_on_native_failure(self):
        flow=(self.root/DISPATCH).read_text()
        job=flow.split('  build-debug-apk:',1)[1].split('  a07-native-debug-build:',1)[0]
        self.assertNotIn('failure()',job)
        self.assertNotIn('always()',job)
        self.assertIn("inputs.a05_mode != 'native-only'",job)

if __name__=='__main__':unittest.main()
