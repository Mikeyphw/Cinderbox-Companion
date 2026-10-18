"""M24 PICS branch manifest identity and device runner negative parser tests."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m24_pics_gate as gate
import m24_pics_device_run as runner
from m14_device_qualification import DeviceGateError
class PicsTests(unittest.TestCase):
 def test_source_contract(self):
  receipt=gate.generate()
  self.assertEqual(receipt['overall'],'PASS_PICS_IDENTITY_SOURCE_ONLY')
  self.assertFalse(receipt['signed_depot_file_manifest_verified'])
 def test_negative_identity(self):
  with self.assertRaisesRegex(ValueError,'GITHUB_SHA_MISMATCH'):gate.generate(env={'GITHUB_SHA':'0'*40})
  with self.assertRaisesRegex(ValueError,'REPO_MISMATCH'):gate.generate(env={'GITHUB_REPOSITORY':'other/no'})
 def test_device_parser(self):
  lines=[]
  for m in runner.METHODS:lines+=['INSTRUMENTATION_STATUS: test='+m,'INSTRUMENTATION_STATUS_CODE: 0']
  lines+=['INSTRUMENTATION_CODE: -1']
  self.assertEqual(4,runner.parse('\n'.join(lines))['completed'])
 def test_partial_device_result_rejected(self):
  raw='INSTRUMENTATION_STATUS: test='+runner.METHODS[0]+'\nINSTRUMENTATION_STATUS_CODE: 0\nINSTRUMENTATION_CODE: -1'
  with self.assertRaises(DeviceGateError):runner.parse(raw)
if __name__=='__main__':unittest.main()
