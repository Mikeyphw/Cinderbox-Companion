"""Hermetic adversarial fixtures: NO live Nexus access and NO network calls."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import io
from contextlib import redirect_stderr
import nex_r2c_live_probe as live

KEY = 'fictional-token-for-tests-only'


def source(root):
    f=root/'app/src/main/java/com/sdvsync/mods/api/NexusCatalogOperation.kt'
    f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text('''val clauses = mapOf("gameId" to mapOf("value" to "1303", "op" to "EQUALS"))
val NEXUS_SEARCH_PAGE_SIZE = 50
 document = """query CinderboxCatalog(${'$'}filter: ModsFilter!, ${'$'}sort: [ModsSort!], ${'$'}offset: Int!) {
 mods(filter: ${'$'}filter, sort: ${'$'}sort, offset: ${'$'}offset, count: $NEXUS_SEARCH_PAGE_SIZE) {
 nodes { modId modCategory { name } updatedAt } totalCount } }"""''')
    return root


def gql(ids=(12,), total=1):
    return {'data': {'mods': {'totalCount':total,'nodes': [
        {'modId':n,'modCategory':{'name':'Utilities'},'updatedAt':'2025-01-01T00:00:00Z'}
        for n in ids]}}}


class ProviderTests(unittest.TestCase):
    def test_normal_read_only_path_and_no_secret_in_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen=[]
            def transport(url,key,body=None):
                seen.append((url,key,body))
                if url==live.GRAPHQL:return gql()
                if url.endswith('/files.json'):return {'files':[]}
                return {'mod_id':12}
            result=live.probe(KEY,root=source(Path(tmp)),transport=transport)
            self.assertTrue(result['live_provider_verified'])
            self.assertFalse(result['native_app_navigation_verified'])
            self.assertEqual(3,len(seen))
            self.assertNotIn(KEY,str(result))
            self.assertEqual(['POST','GET','GET'],['POST' if x[2] else 'GET' for x in seen])
            self.assertIn('modCategory { name }',seen[0][2]['query'])
            self.assertEqual('1303',seen[0][2]['variables']['filter']['filter'][0]['gameId']['value'])

    def test_bad_auth_or_graphql_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            def transport(url,key,body=None):return {'errors':[{'message':'secret '+KEY}]}
            with self.assertRaisesRegex(live.ProbeRefusal,'SCHEMA_OR_AUTH'):
                live.probe(KEY,root=source(Path(tmp)),transport=transport)

    def test_bad_provider_ids_and_wrong_detail_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=source(Path(tmp))
            for raw_id in [0,True,-1,'12',2147483648,None]:
                with self.assertRaises(live.ProbeRefusal):
                    live.probe(KEY,root=root,transport=lambda *_:gql((raw_id,),1))
            def transport(url,key,body=None):
                return gql() if url==live.GRAPHQL else {'mod_id':13}
            with self.assertRaisesRegex(live.ProbeRefusal,'DETAIL_ID_MISMATCH'):
                live.probe(KEY,root=root,transport=transport)

    def test_missing_or_invalid_category_and_date_refuse(self):
        for bad in [{'modCategory':'Utilities'}, {'modCategory':{'x':'y'}},
                    {'updatedAt':1710000000},{'updatedAt':'invalid'}]:
            row=gql()['data']['mods']['nodes'][0];row.update(bad)
            with self.assertRaises(live.ProbeRefusal):live.validate_page({'data':{'mods':{'totalCount':1,'nodes':[row]}}},0)

    def test_pagination_uses_offset_50_and_never_invents_full_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            offsets=[]
            def transport(url,key,body=None):
                if url==live.GRAPHQL:
                    offset=body['variables']['offset'];offsets.append(offset)
                    return gql(range(1,51),51) if offset==0 else gql((51,),51)
                if url.endswith('/files.json'):return {'files':[]}
                return {'mod_id':1}
            result=live.probe(KEY,root=source(Path(tmp)),transport=transport)
            self.assertEqual([0,50],offsets)
            self.assertTrue(result['second_page_checked'])

    def test_malformed_count_and_endpoint_denied(self):
        for count in [True, '2',-1,None,3.2]:
            with self.assertRaises(live.ProbeRefusal):live.validate_page(gql((12,),count),0)
        with self.assertRaisesRegex(live.ProbeRefusal,'ENDPOINT_NOT_ALLOWLISTED'):
            live.request_json('https://example.org/','secret')

    def test_no_key_refuses_before_any_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(live.ProbeRefusal,'NEXUS_KEY_REQUIRED'):
                live.probe('',root=source(Path(tmp)),transport=lambda *_:self.fail('no request allowed'))

    def test_source_query_change_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=source(Path(tmp))
            f=root/'app/src/main/java/com/sdvsync/mods/api/NexusCatalogOperation.kt'
            f.write_text(f.read_text().replace('modCategory { name }','categoryName: category'))
            with self.assertRaisesRegex(live.ProbeRefusal,'SOURCE_QUERY_CONTRACT_DRIFT'):
                live.query_from_source(root)

    def test_cli_does_not_print_secret_or_create_receipt_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'receipt.json'
            err=io.StringIO()
            with patch('sys.argv',['probe','--receipt',str(dest)]),\
                 patch.dict('os.environ',{'CINDERBOX_NEXUS_API_KEY': ''}),redirect_stderr(err):
                self.assertEqual(1,live.main())
            self.assertFalse(dest.exists());self.assertNotIn(KEY,err.getvalue())

if __name__=='__main__':unittest.main(verbosity=2)
