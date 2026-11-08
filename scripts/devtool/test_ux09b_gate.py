"""UX-09B red tests on forbidden policy drift and fake visual acceptance."""
import json,tempfile,unittest
from pathlib import Path
import ux09b_gate as gate

class UX09BSourceTest(unittest.TestCase):
    def fixture(self,where):
        root=Path(where)
        items=set(gate.FILES)|{'design/cinderbox/01_REFERENCE/cinderbox-portrait-DARK.html'}
        for path in items:
            dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((gate.ROOT/path).read_bytes())
        return root

    def test_nominal(self):
        self.assertEqual(gate.check()['native_candidate_states'],17)

    def test_tampered_reference_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            file=root/'design/cinderbox/01_REFERENCE/cinderbox-portrait-DARK.html'
            file.write_text(file.read_text()+'\n<!-- UNAPPROVED CHANGE -->\n')
            with self.assertRaisesRegex(AssertionError,'REFERENCE_HASH_DRIFT'):
                gate.check(root)

    def test_unsafe_test_mutation_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            file=root/gate.FILES[0]
            file.write_text(file.read_text()+'\n// startDownload( is prohibited\n')
            with self.assertRaisesRegex(AssertionError,'UNSAFE_TEST'):
                gate.check(root)

    def test_reintroducing_direct_data_shutdown_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            file=root/'scripts/devtool/ux09b_emulator_ci.sh'
            file.write_text(file.read_text()+'\nadb -s "$serial" shell svc data disable\n')
            with self.assertRaisesRegex(AssertionError,'UX09B_UNSAFE_RADIO_SETUP'):
                gate.check(root)

    def test_removing_shared_airplane_gate_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            file=root/'scripts/devtool/ux09b_emulator_ci.sh'
            file.write_text(file.read_text().replace(
                'python3 -B scripts/devtool/r48_offline_gate.py --serial "$serial"',
                '# offline gate was removed'))
            with self.assertRaisesRegex(AssertionError,'UX09B_OFFLINE_GATE_MISSING'):
                gate.check(root)

    def test_weakened_shared_connectivity_gate_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            file=root/'scripts/devtool/r48_offline_gate.py'
            file.write_text(file.read_text().replace('ACTIVE_DEFAULT_NETWORK_REFUSED',
                                                     'IGNORE_ACTIVE_DEFAULT_NETWORK'))
            with self.assertRaisesRegex(AssertionError,'UX09B_OFFLINE_CONTRACT_MISSING'):
                gate.check(root)

    def test_release_flag_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp)
            file=root/'docs/security/M3_RELEASE_POLICY.json'
            policy=json.loads(file.read_text());policy['release_enabled']=True
            file.write_text(json.dumps(policy))
            with self.assertRaisesRegex(AssertionError,'RELEASE_GATE_DRIFT'):
                gate.check(root)

if __name__=='__main__':unittest.main()
