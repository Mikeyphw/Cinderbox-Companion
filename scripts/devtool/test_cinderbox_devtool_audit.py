"""Adversarial offline checks for the local Devtool source contract."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('cinderbox_devtool_audit.py')
spec = importlib.util.spec_from_file_location('cinderbox_devtool_audit', SCRIPT)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)
ROOT = SCRIPT.parents[2]


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('.devtool.toml', 'gradle/wrapper/gradle-wrapper.properties',
                     '.github/workflows/devtool-android-build.yml',
                     '.github/workflows/build.yml',
                     '.github/workflows/devtool-source-contract.yml',
                     'scripts/devtool/hosted_debug.py'):
            dst = self.root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dst)

    def test_unmodified_contract(self):
        r = audit_module.audit(self.root)
        self.assertTrue(r['ok'], r['issues'])
        self.assertFalse(r['gradle_executed'])

    def test_rejects_unreviewed_local_default(self):
        p=self.root/'.devtool.toml'
        p.write_text(p.read_text().replace('default_command = "host-check"',
                                          'default_command = "build"',1))
        self.assertIn('UNSAFE_WRAPPER_DEFAULT', audit_module.audit(self.root)['issues'])

    def test_rejects_unpinned_distribution(self):
        p=self.root/'gradle/wrapper/gradle-wrapper.properties'
        p.write_text(p.read_text().replace('distributionSha256Sum=', 'notPinned='))
        self.assertIn('UNPINNED_GRADLE_DISTRIBUTION', audit_module.audit(self.root)['issues'])

    def test_rejects_new_actions_wrapper_not_supported_by_pinned_engines(self):
        p=self.root/'.devtool.toml'
        p.write_text(p.read_text()+"\n[wrapper.commands.ci-debug-plan]\ndevtool = \"actions\"\n[wrapper.commands.ci-debug-plan.actions]\noperation = \"plan\"\n")
        self.assertIn('PINNED_DEVTOOL_INCOMPATIBLE_WRAPPER:ci-debug-plan',
                      audit_module.audit(self.root)['issues'])

    def test_rejects_security_job_without_bytecode_protection(self):
        p=self.root/'.devtool.toml'
        p.write_text(p.read_text().replace(
            'env = { PYTHONDONTWRITEBYTECODE = "1" }', '', 1))
        self.assertIn('HOST_JOB_NOT_PYTHON_ONLY:security-contract',audit_module.audit(self.root)['issues'])

    def test_rejects_malformed_host_command(self):
        p=self.root/'.devtool.toml'
        p.write_text(p.read_text().replace(
            'command = ["python3", "-B", "scripts/devtool/cinderbox_devtool_audit.py", "--json"]',
            'command = "python3 -B scripts/devtool/cinderbox_devtool_audit.py"', 1))
        self.assertIn('HOST_JOB_NOT_PYTHON_ONLY:devtool-contract',audit_module.audit(self.root)['issues'])

    def test_rejects_unsafe_host_gradle(self):
        p=self.root/'.devtool.toml'
        p.write_text(p.read_text().replace('command = ["python3", "-B", "scripts/devtool/cinderbox_devtool_audit.py", "--json"]',
                         'command = ["./gradlew", ":app:assembleDebug"]',1))
        self.assertIn('HOST_JOB_NOT_PYTHON_ONLY:devtool-contract',audit_module.audit(self.root)['issues'])


if __name__=='__main__': unittest.main()
