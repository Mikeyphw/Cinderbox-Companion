"""Negative source-contract mutations without Android builds or device access."""
import json,tempfile,unittest
from pathlib import Path
import ux09a_gate as gate

class UX09ARegression(unittest.TestCase):
    def fixture(self,temp):
        root=Path(temp)
        needed=set(gate.UI)|{gate.TEST,
           'design/cinderbox/02_CONTRACT/ux-contract.json',
           'app/src/main/java/com/sdvsync/ui/theme/Theme.kt',
           'app/src/main/java/com/sdvsync/ui/theme/CinderboxDarkTokens.kt',
           'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt',
           'docs/security/M3_RELEASE_POLICY.json',
           'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',
           '.github/workflows/cinderbox-ux09a-native-parity.yml',
           'scripts/devtool/ux09a_emulator_ci.sh'}
        for relative in needed:
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((gate.ROOT/relative).read_bytes())
        return root

    def test_nominal(self):
        self.assertEqual(gate.check()['required_tags'],21)

    def test_missing_steam_status_tag_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/'app/src/main/java/com/sdvsync/ui/screens/HomeScreen.kt'
            p.write_text(p.read_text().replace('"cinderbox.steam.connection-status"','"drift"'))
            with self.assertRaisesRegex(AssertionError,'UX09A_UI_TAG_MISSING'):
                gate.check(root)

    def test_missing_native_method_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/gate.TEST
            p.write_text(p.read_text().replace('fun steamCloudLockedWithoutAuthentication(', 'fun deletedCloudTest('))
            with self.assertRaisesRegex(AssertionError,'UX09A_TEST_MISSING'):
                gate.check(root)

    def test_release_flag_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/'docs/security/M3_RELEASE_POLICY.json'
            obj=json.loads(p.read_text());obj['release_enabled']=True
            p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(AssertionError,'UX09A_RELEASE_GUARD'):
                gate.check(root)

if __name__=='__main__':unittest.main()
