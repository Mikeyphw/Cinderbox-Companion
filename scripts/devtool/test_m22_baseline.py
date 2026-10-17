"""M22 source, provenance, safety and adversarial receipt checks."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m22_baseline as m

class M22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = m.read_json(m.ROOT, str(m.MANIFEST))
        cls.config = m.tomllib.loads((m.ROOT / '.devtool.toml').read_text())

    def test_historical_anchors_stay_distinct_from_new_results(self):
        m.check_contract(self.base)
        h = self.base['historical_acceptance']
        self.assertEqual(h['m14_m20']['observations_reported_pass'], 74)
        self.assertEqual(h['m21']['observations_reported_pass'], 18)
        self.assertEqual(h['total_reported_pass_observations'], 92)
        self.assertEqual(h['m21']['availability'], 'NOT_ATTACHED')

    def test_forged_historical_count_rejected(self):
        bad = copy.deepcopy(self.base)
        bad['historical_acceptance']['total_reported_pass_observations'] = 93
        with self.assertRaises(m.BaselineError): m.check_contract(bad)

    def test_fake_original_receipt_claim_rejected(self):
        bad = copy.deepcopy(self.base)
        bad['historical_acceptance']['m21']['original_receipts_in_repository'] = True
        with self.assertRaises(m.BaselineError): m.check_contract(bad)

    def test_manufactured_m23_device_pass_rejected(self):
        bad = copy.deepcopy(self.base)
        bad['coverage_matrix']['M23']['device_campaign'] = 'PASS'
        with self.assertRaises(m.BaselineError): m.check_contract(bad)

    def test_release_policy_and_historic_links_present(self):
        a = m.produce(m.ROOT, {})
        self.assertEqual(a['overall'], 'PASS_M22_HOST_INVENTORY')
        self.assertFalse(a['publication_enabled'])
        self.assertFalse(a['historical_receipts_overwritten'])
        self.assertEqual(a['historical_observations']['original_receipts'], 'NOT_ATTACHED')
        self.assertEqual(a['source']['github_checkout_binding'], 'NOT_PROVIDED')
        self.assertEqual(a['milestone_qualification'], 'INCOMPLETE_ORIGINAL_RECEIPTS_AND_NEW_CI')

    def test_current_source_receipt_revalidates(self):
        a = m.produce(m.ROOT, {})
        m.verify_report(a, m.ROOT, {})

    def test_tampered_receipt_fails_digest(self):
        a = m.produce(m.ROOT, {})
        a['historical_observations']['m21_pass_reported'] = 19
        with self.assertRaises(m.BaselineError): m.verify_report(a, m.ROOT, {})

    def test_self_rehashed_receipt_fails_independent_recompute(self):
        a = m.produce(m.ROOT, {})
        a['milestone_qualification'] = 'PASS_RELEASE'
        a.pop('receipt_sha256')
        a['receipt_sha256'] = m.digest(m.canonical(a))
        with self.assertRaises(m.BaselineError): m.verify_report(a, m.ROOT, {})

    def test_github_sha_mismatch_fails_closed(self):
        env = {'GITHUB_SHA': '0'*40, 'GITHUB_REPOSITORY': m.REPO, 'GITHUB_RUN_ID': '39040952179'}
        with self.assertRaises(m.BaselineError): m.produce(m.ROOT, env)

    def test_github_repo_mismatch_fails_closed(self):
        with self.assertRaises(m.BaselineError): m.produce(m.ROOT, {'GITHUB_REPOSITORY': 'attacker/fork'})

    def test_github_run_id_invalid_fails_closed(self):
        with self.assertRaises(m.BaselineError): m.produce(m.ROOT, {'GITHUB_RUN_ID': 'abc'})

    def test_workflow_dag_is_complete_and_non_device(self):
        d = m.inventory_devtool(self.config)
        self.assertGreaterEqual(d['workflow_count'], 10)
        self.assertGreaterEqual(d['workflows']['m22-check']['node_count'], 3)
        self.assertEqual(d['android_device_execution'], 'EXPLICIT_ONLY')

    def test_workflow_cycle_rejected(self):
        cfg = copy.deepcopy(self.config)
        cfg['targets']['cinderbox']['workflows']['m22-check'] = [
            {'id': 'a', 'ref': 'job:m22-baseline', 'depends_on': ['b']},
            {'id': 'b', 'ref': 'job:m22-host-tests', 'depends_on': ['a']},
        ]
        with self.assertRaises(m.BaselineError): m.inventory_devtool(cfg)

    def test_missing_workflow_dependency_rejected(self):
        cfg = copy.deepcopy(self.config)
        cfg['targets']['cinderbox']['workflows']['m22-check'] = [
            {'id': 'x', 'ref': 'job:m22-baseline', 'depends_on': ['absent']}
        ]
        with self.assertRaises(m.BaselineError): m.inventory_devtool(cfg)

    def test_traversal_rejected(self):
        with self.assertRaises(m.BaselineError): m.safe_file(m.ROOT, '../secret')

    def test_symlink_component_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'actual').mkdir()
            (base / 'actual' / 'test').write_text('x')
            os.symlink(base / 'actual', base / 'link')
            with self.assertRaises(m.BaselineError): m.safe_file(base, 'link/test')

    def test_historical_ci_identity_tamper_rejected(self):
        bad = copy.deepcopy(self.base)
        bad['historical_ci_anchors'][0]['run_id'] = 'not-id'
        with self.assertRaises(m.BaselineError): m.check_contract(bad)

if __name__ == '__main__': unittest.main()
