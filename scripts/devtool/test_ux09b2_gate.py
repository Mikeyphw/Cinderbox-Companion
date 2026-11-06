"""Offline regression tests: missing real routes, permission actions and release drift fail closed."""
import json, tempfile, unittest
from pathlib import Path
import ux09b2_gate as gate

class UX09B2GateTests(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp)
        extra={'design/cinderbox/01_REFERENCE/cinderbox-portrait-DARK.html'}
        for name in set(gate.FILES)|extra:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((gate.ROOT/name).read_bytes())
        return root

    def test_nominal(self):
        self.assertEqual(gate.check()['native_cases_after_hosted_run'],21)

    def test_navigation_removed_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/gate.FILES[0]
            p.write_text(p.read_text().replace('"cinderbox.more.operations"','"replaced.navigation"'))
            with self.assertRaisesRegex(AssertionError,'UX09B2_REAL_NAV_MISSING'):
                gate.check(root)

    def test_privileged_test_call_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/gate.FILES[0]
            p.write_text(p.read_text()+'\n// requestShizukuPermission( not allowed\n')
            with self.assertRaisesRegex(AssertionError,'UX09B2_UNSAFE_INSTRUMENTATION'):
                gate.check(root)

    def test_release_enabled_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);p=root/gate.FILES[5]
            data=json.loads(p.read_text());data['publication_enabled']=True;p.write_text(json.dumps(data))
            with self.assertRaisesRegex(AssertionError,'UX09B2_POLICY_DRIFT'):
                gate.check(root)

if __name__=='__main__':unittest.main()
