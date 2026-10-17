"""UI-D03 offline source contract and computed contrast regression tests."""
import unittest
from ui_d03_source import verify,parse_colors,PAIRS,ROOT,THEME

class EarthyD03HostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=verify()

    def test_checks_all_pass(self):
        self.assertEqual(self.result['overall'],'PASS_HOST_STATIC',self.result['checks'])

    def test_real_kotlin_palette_parsed(self):
        schemes=parse_colors((ROOT/THEME).read_text())
        self.assertEqual(set(schemes),{'light','dark'})
        self.assertEqual(schemes['light']['primary'],'#3F5744')
        self.assertEqual(schemes['dark']['primary'],'#A8BBA0')

    def test_functional_contrast_all_pairs(self):
        self.assertEqual(len(self.result['contrast_ratios']),len(PAIRS)*2)
        self.assertTrue(all(r is not None and r>=4.5 for r in self.result['contrast_ratios'].values()),self.result['contrast_ratios'])

    def test_device_claims_are_not_fabricated(self):
        self.assertEqual(self.result['device_tests'],'NOT_RUN')
        self.assertEqual(self.result['screenshots'],'NOT_CAPTURED')
        self.assertFalse(self.result['release_qualified'])
        self.assertFalse(self.result['publication_allowed'])

    def test_d03_no_release_enablement(self):
        self.assertTrue(self.result['checks']['release_still_disabled'])

if __name__=='__main__':unittest.main()
