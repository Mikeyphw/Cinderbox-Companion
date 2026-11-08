"""Fail-closed regression fixtures for provider boundary contract (no API traffic)."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import nex_r2b_gate as gate

FILES = (
 gate.API+'NexusModSource.kt', gate.API+'NexusProviderIntegrity.kt',
 'app/src/test/java/com/sdvsync/mods/api/NexusProviderIntegrityTest.kt',
 'docs/devtool/NEX_R2B_PROVIDER_CONTRACT.md',
 '.github/workflows/nex-r2b-provider-integrity.yml',
 'docs/security/M3_RELEASE_POLICY.json',
 gate.FIX+'graphql_browse.schema_shaped.json',
 gate.FIX+'v1_files.schema_shaped.json'
)


class BoundaryTests(unittest.TestCase):
    def fixture(self, folder):
        root=Path(folder)
        for name in FILES:
            src=gate.ROOT/name; target=root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,target)
        return root

    def mutate(self, name, find, replace, expected):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t); f=root/name
            text=f.read_text()
            self.assertIn(find,text)
            f.write_text(text.replace(find,replace))
            self.assertIn(expected,gate.check(root))

    def test_nominal(self): self.assertEqual([],gate.check())

    def test_missing_positive_id_guard(self):
        self.mutate(gate.API+'NexusModSource.kt',
            'NexusProviderIntegrity.positiveId(node.opt("modId"))', 'node.optInt("modId")',
            'NEX_R2B_MISSING:strict graphql ids')

    def test_no_default_count_allowed(self):
        self.mutate(gate.API+'NexusModSource.kt',
            'NexusProviderIntegrity.totalCount(data.opt("totalCount"))', 'data.optInt("totalCount",0)',
            'NEX_R2B_MISSING:strict graphql count')

    def test_unknown_category_not_assumed_main(self):
        self.mutate(gate.API+'NexusProviderIntegrity.kt', '"UNSPECIFIED"', '"MAIN"',
            'NEX_R2B_MISSING:file category')

    def test_misleading_live_label_refused(self):
        self.mutate(gate.FIX+'graphql_browse.schema_shaped.json',
            'synthetic_schema_shaped_not_live_nexus', 'live_authenticated_provider_capture',
            'NEX_R2B_FIXTURE_PROVENANCE:graphql_browse.schema_shaped.json')

    def test_missing_adversarial_node_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t); p=root/(gate.FIX+'graphql_browse.schema_shaped.json')
            raw=json.loads(p.read_text());raw['data']['mods']['nodes']=[raw['data']['mods']['nodes'][0]]
            p.write_text(json.dumps(raw))
            self.assertIn('NEX_R2B_BROWSE_ADVERSARIAL_FIXTURE_DRIFT',gate.check(root))

    def test_release_policy_drift_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.fixture(t);p=root/'docs/security/M3_RELEASE_POLICY.json'
            data=json.loads(p.read_text());data['release_enabled']=True;p.write_text(json.dumps(data))
            self.assertIn('NEX_R2B_RELEASE_POLICY_DRIFT:release_enabled',gate.check(root))

    def test_alien_browse_script_refused(self):
        self.mutate(gate.API+'NexusProviderIntegrity.kt', 'internal object NexusProviderIntegrity {',
                    'internal object NexusProviderIntegrity {\n    // WebView(',
                    'NEX_R2B_UNSAFE_ADDITION:WebView(')

    def test_no_duplicate_emulator_workflow(self):
        self.mutate('.github/workflows/nex-r2b-provider-integrity.yml',
                    'name: NEX-R2B Provider Integrity and JVM Mapping',
                    'name: NEX-R2B Provider Integrity and JVM Mapping\n# android-emulator-runner',
                    'NEX_R2B_MISSING:no duplicated emulator')


if __name__ == '__main__':unittest.main(verbosity=2)
