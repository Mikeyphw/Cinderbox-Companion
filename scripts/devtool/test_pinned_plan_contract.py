"""Exact-shape fixtures from pinned Devtool A05/A07 hosted CLI."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('pinned_plan_contract',Path(__file__).with_name('pinned_plan_contract.py'))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PinnedPlanContractTests(unittest.TestCase):
    def good(self):
        return {
            'schema_version': 1,
            'machine': {'operation': {'command': 'plan','status': 'ok'}},
            'data': {'schema_version': 2, 'action': 'm24-verify-ux-check',
                     'targets': ['cinderbox'], 'summary': {'node_count': 2},
                     'commands': [{'argv':['python3','-B','test.py']}]}}

    def test_valid_real_envelope(self):
        self.assertEqual(mod.validate_receipt(self.good(),'m24-verify-ux-check','a05'),2)

    def test_old_flat_parser_is_rejected(self):
        receipt=self.good()['data']
        with self.assertRaisesRegex(ValueError,'INVALID_PINNED_DEVTOOL'):
            mod.validate_receipt(receipt,'m24-verify-ux-check','a05')

    def test_refuses_failed_operation_despite_valid_data(self):
        receipt=self.good();receipt['machine']['operation']['status']='failed'
        with self.assertRaises(ValueError):
            mod.validate_receipt(receipt,'m24-verify-ux-check','a05')

    def test_refuses_wrong_action_or_target(self):
        with self.assertRaises(ValueError):
            mod.validate_receipt(self.good(),'build','a05')
        receipt=self.good();receipt['data']['targets']=['other']
        with self.assertRaises(ValueError):
            mod.validate_receipt(receipt,'m24-verify-ux-check','a05')

    def test_refuses_no_commands_or_zero_nodes(self):
        receipt=self.good();receipt['data']['commands']=[]
        with self.assertRaises(ValueError):
            mod.validate_receipt(receipt,'m24-verify-ux-check','a05')
        receipt=self.good();receipt['data']['summary']['node_count']=0
        with self.assertRaises(ValueError):
            mod.validate_receipt(receipt,'m24-verify-ux-check','a05')

    def test_valid_a07_plan(self):
        receipt=self.good();receipt['data']['action']='build'
        self.assertEqual(mod.validate_receipt(receipt,'build','a07'),2)
