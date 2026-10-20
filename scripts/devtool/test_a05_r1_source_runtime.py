"""A05-R1: checked-out source outranks an installed wheel with missing package data."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/devtool'))
import a05_actions_qualification as a05

class A05R1RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow=(ROOT/a05.WORKFLOW).read_text('utf-8').split('  a05-native-devtool-dag:',1)[1]

    def test_pinned_runtime_source_guard(self):
        self.assertIn('test "$(git -C "$RUNNER_TEMP/devtool-a05" rev-parse HEAD)" = "$A05_DEVTOOL_SHA"',self.flow)
        self.assertIn('test -s "$RUNNER_TEMP/devtool-a05/devtool/core_cli_schema.json"',self.flow)
        self.assertIn('actual != expected.resolve()',self.flow)
        self.assertIn('canonical_cli_schema()',self.flow)

    def test_all_three_cli_steps_are_source_bound(self):
        self.assertEqual(self.flow.count('export PYTHONPATH="$RUNNER_TEMP/devtool-a05"'),3)
        plan=self.flow.split('      - name: Native target-local DAG plan and preflight',1)[1].split('      - name:',1)[0]
        invoke=self.flow.split('      - name: Invoke native DAG and retain machine evidence',1)[1].split('      - name:',1)[0]
        for step in (plan,invoke):
            self.assertLess(step.index('export PYTHONPATH='),step.index('-m devtool'))
        self.assertIn('preflight --target cinderbox --workflow m24-verify-ux-check',plan)
        self.assertIn('--machine-file "$RUNNER_TEMP/devtool-invoke.json" invoke',invoke)

    def test_missing_wheel_data_can_be_served_from_immutable_source(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); src=base/'frozen'; installed=base/'site'
            (src/'devtool').mkdir(parents=True)
            (installed/'devtool').mkdir(parents=True)
            (src/'devtool/__init__.py').write_text('ORIGIN="frozen"\n')
            (installed/'devtool/__init__.py').write_text('ORIGIN="broken-wheel"\n')
            (src/'devtool/core_cli_schema.json').write_text('{"schema_version": 2}')
            code='import devtool;from pathlib import Path;assert devtool.ORIGIN=="frozen";assert (Path(devtool.__file__).parent/"core_cli_schema.json").is_file()'
            env=os.environ.copy();env['PYTHONPATH']=str(src)+os.pathsep+str(installed)
            p=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=10,cwd=base)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_missing_checked_out_schema_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); (base/'devtool').mkdir()
            (base/'devtool/__init__.py').write_text('')
            env=os.environ.copy();env['PYTHONPATH']=str(base)
            p=subprocess.run([sys.executable,'-c','from pathlib import Path; import devtool; assert (Path(devtool.__file__).parent/"core_cli_schema.json").is_file()'],env=env,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(p.returncode,0)

    def test_original_failed_run_cannot_be_promoted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); p.mkdir(exist_ok=True)
            a05.record(p/'evidence','b7559c0277f34e3ada9638ef605b6af68ec658ee',a05.DEVTOOL_SHA,a05.REPO,39296491876,1,p)
            with self.assertRaises(a05.ProofError):
                a05.verify_local(p/'evidence',run_id=39296491876,attempt=1,source_sha='b7559c0277f34e3ada9638ef605b6af68ec658ee')

    def test_do_not_enable_android_device_or_release(self):
        self.assertIn("if: ${{ inputs.a05_mode == 'native-only' || inputs.a05_mode == 'both' }}",self.flow)
        for flag in ('adb install','sudo ','secrets.','assembleRelease','contents: write'):
            self.assertNotIn(flag,self.flow)

    def test_existing_source_contract_is_still_valid(self):
        self.assertEqual(a05.source()['overall'],'PASS_CINDERBOX_A05_SOURCE_CONTRACT')

if __name__=='__main__': unittest.main()
