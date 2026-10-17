"""Read-only UI-D02 source tests; no device/build or historical evidence edits."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_d02_source import verify


class EarthyD02Tests(unittest.TestCase):
    def test_component_semantics(self):
        receipt = verify()
        self.assertEqual('PASS_SOURCE_CONTRACT', receipt['overall'], receipt['checks'])

    def test_qualifications_remain_unset(self):
        receipt = verify()
        self.assertFalse(receipt['release_qualified'])
        self.assertFalse(receipt['publication_allowed'])
        self.assertTrue(receipt['historical_m21_results_replaced'] is False)
        self.assertEqual('NOT_RUN', receipt['device_tests'])

    def test_checked_inventory_nonempty_and_stable(self):
        receipt = verify()
        self.assertGreaterEqual(len(receipt['source_sha256']), 9)
        self.assertTrue(all(len(digest)==64 for digest in receipt['source_sha256'].values()))


if __name__ == '__main__':
    unittest.main()
