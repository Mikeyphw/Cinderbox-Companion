"""Source contract adversarial fixtures; never connect to the provider."""
import json,shutil,tempfile,unittest
from pathlib import Path
import nex_r2c_gate as gate

class SourceTests(unittest.TestCase):
    def fixture(self,where):
        root=Path(where)
        for rel in gate.FILES:
            f=root/rel;f.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(gate.ROOT/rel,f)
        return root

    def mutate(self,path,before,after,reason):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);f=root/path;s=f.read_text()
            self.assertIn(before,s);f.write_text(s.replace(before,after))
            self.assertIn('NEX_R2C_MISSING:'+reason,gate.check(root))

    def test_nominal(self):self.assertEqual([],gate.check())
    def test_missing_graphql_nested_category_refused(self):
        self.mutate(gate.FILES[0],'modCategory { name }','categoryName: category','graphql nested category')
    def test_missing_updated_field_refused(self):
        self.mutate(gate.FILES[0],'                  updatedAt\n','                  wrongDate\n','graphql updatedAt')
    def test_missing_safe_category_parser_refused(self):
        self.mutate(gate.FILES[1],'node.optJSONObject("modCategory")?.optString("name", "")',
                    'node.optString("categoryName", "")','safe nested mapping')
    def test_missing_bounded_date_parser_refused(self):
        self.mutate(gate.FILES[2],'java.time.Instant.parse(raw.trim())','raw.toLong()','bounded ISO date')
    def test_creds_cannot_be_hardcoded(self):
        self.mutate(gate.FILES[5],"os.environ.get('CINDERBOX_NEXUS_API_KEY', '')",
                    "'HARDCODED_TOKEN'",'secret from environment only')
    def test_live_workflow_never_auto_on_pr(self):
        self.mutate(gate.FILES[7],"if: github.event_name == 'workflow_dispatch'",
                    'if: always()','no auto live check on PR')
    def test_privacy_policy_drift_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);p=root/gate.FILES[-1]
            obj=json.loads(p.read_text());obj['publication_enabled']=True
            p.write_text(json.dumps(obj))
            self.assertIn('NEX_R2C_RELEASE_POLICY_DRIFT:publication_enabled',gate.check(root))
    def test_unsafe_addition_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);p=root/gate.FILES[5]
            p.write_text(p.read_text()+'\n# WebView(\n')
            self.assertIn('NEX_R2C_UNSAFE_OPERATION:WebView(',gate.check(root))

if __name__=='__main__':unittest.main(verbosity=2)
