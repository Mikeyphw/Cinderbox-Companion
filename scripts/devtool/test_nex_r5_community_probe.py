#!/usr/bin/env python3
"""No-network source/receipt/negative tests for the read-only community API probe."""
from __future__ import annotations
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
import nex_r5_community_probe as p

FIXTURES = Path(__file__).resolve().parent/'fixtures'/'nex_r5_community'


def fixture(name):
    return json.loads((FIXTURES/name).read_text())


class CommunityProbeTests(unittest.TestCase):
    def test_current_documented_graphql_is_not_mod_scoped(self):
        report = p.assess_schema(fixture('documented_v2_schema.json'), '123')
        self.assertEqual('NO_MOD_SCOPED_CONTRACT', report['status'])
        self.assertFalse(report['posts']['candidate_found'])
        self.assertFalse(report['media']['candidate_found'])
        self.assertTrue(report['posts']['thread_by_id_available'])
        self.assertTrue(report['media']['site_wide_search_available'])
        self.assertFalse(report['native_qualified'])
        self.assertEqual('READ', report['schema_status'])

    def test_future_schema_is_candidate_only_not_native_proof(self):
        report = p.assess_schema(fixture('hypothetical_mod_scoped_schema.json'))
        self.assertEqual('CANDIDATES_UNVERIFIED', report['status'])
        self.assertTrue(report['posts']['candidate_found'])
        self.assertTrue(report['media']['candidate_found'])
        self.assertEqual(['modUid'], report['media']['mod_scoped_filter_fields'])
        self.assertFalse(report['native_qualified'])

    def test_thread_id_is_not_mod_id(self):
        data=fixture('documented_v2_schema.json')
        data['data']['root']['fields'].append({'name':'modComments','args':[{'name':'commentThreadId'}]})
        self.assertFalse(p.assess_schema(data)['posts']['candidate_found'])

    def test_user_search_or_owner_not_mod_scoped(self):
        data=fixture('documented_v2_schema.json')
        data['data']['mediaFilter']['inputFields'].extend([{'name':'author'},{'name':'description'},{'name':'owner'}])
        self.assertFalse(p.assess_schema(data)['media']['candidate_found'])

    def test_only_mod_relevant_root_operators_count(self):
        data=fixture('documented_v2_schema.json')
        data['data']['root']['fields'].append({'name':'modMedia','args':[{'name':'gameId'},{'name':'modUid'}]})
        self.assertEqual(['modMedia'],p.assess_schema(data)['media']['mod_scoped_root_fields'])

    def test_bad_graphql_envelope_fails_closed(self):
        self.assertEqual('INCONCLUSIVE',p.assess_schema({'errors':[{'message':'token ABC'}]})['status'])
        self.assertEqual('INCONCLUSIVE',p.assess_schema({'data':{}})['status'])
        with self.assertRaises(ValueError):p.assess_schema([])

    def test_no_live_requests_for_offline_fixture(self):
        with tempfile.TemporaryDirectory() as d, patch.object(p,'query_api',side_effect=AssertionError('NETWORK')):
            out=Path(d)/'probe.json'
            self.assertEqual(0,p.main(['--fixture',str(FIXTURES/'documented_v2_schema.json'),
                                       '--mod-id','7001','--output',str(out)]))
            receipt=json.loads(out.read_text())
            self.assertEqual('7001',receipt['mod_id'])
            self.assertEqual(0o600,out.stat().st_mode & 0o777)

    def test_atomic_no_overwrite_or_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'result'
            p.write_receipt(str(target), {'schema_status':'READ'})
            with self.assertRaises(FileExistsError):p.write_receipt(str(target),{})
            alias=Path(d)/'alias';alias.symlink_to(target)
            with self.assertRaises(ValueError):p.write_receipt(str(alias),{})

    def test_live_http_errors_are_sanitized(self):
        err=urllib.error.HTTPError(p.ENDPOINT,401,'top-secret-token',{},None)
        with patch.object(p,'query_api',side_effect=err):
            receipt=p.probe_live('7001')
        self.assertEqual('HTTP_401',receipt['reason_code'])
        self.assertNotIn('top-secret',json.dumps(receipt))

    def test_live_identity_without_content(self):
        responses=[fixture('documented_v2_schema.json'),
                   {'data': {'mod':{'modId': 7001,'gameId':1303,'uid':'99999'}}}]
        with patch.object(p,'query_api',side_effect=responses) as q:
            result=p.probe_live('7001')
        self.assertEqual('MATCHED',result['identity_lookup'])
        self.assertFalse(result['personal_or_media_content_fetched'])
        self.assertFalse(result['native_qualified'])
        self.assertEqual(p.IDENTITY_QUERY,q.call_args_list[1].args[0])
        self.assertEqual({'modId':'7001','gameId':'1303'},q.call_args_list[1].args[1])

    def test_http_max_response_bound_and_whitelist(self):
        with self.assertRaises(ValueError):p.query_api('mutation{ createComment { id }}')
        self.assertLessEqual(p.MAX_HTTP_BYTES, 1024*1024)
        self.assertEqual('https://api.nexusmods.com/v2/graphql',p.ENDPOINT)

    def test_invalid_id_refused_before_any_http(self):
        with patch.object(p,'query_api',side_effect=AssertionError('network')):
            with patch('sys.stderr',new=io.StringIO()):
                with self.assertRaises(SystemExit):p.main(['--live','--mod-id','../../etc/passwd'])

    def test_graphql_envelope_never_serializes_response_body(self):
        value=p.assess_schema({'errors':[{'message':'PERSONAL-API-KEY-123'}]})
        self.assertNotIn('PERSONAL',json.dumps(value))


if __name__=='__main__': unittest.main(verbosity=2)
