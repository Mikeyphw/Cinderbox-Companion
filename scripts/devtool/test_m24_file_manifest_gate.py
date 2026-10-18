"""M24 bounded cached-manifest content verification; offline source and synthetic Kotlin tests."""
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path
import m24_file_manifest_gate as gate
from m14_device_qualification import DeviceGateError
import m24_file_manifest_device_run as runner
ROOT=Path(__file__).resolve().parents[2]
class ProofTests(unittest.TestCase):
 def test_source_contract(self):
  proof=gate.generate()
  self.assertEqual(proof['overall'],'PASS_M24_DEPOT_FILE_PROOF_SOURCE')
  self.assertFalse(proof['steam_entitlement_verified'])
  self.assertFalse(proof['signed_steam_manifest_verified'])
 def test_negative_source(self):
  with self.assertRaisesRegex(ValueError,'GITHUB_SHA_MISMATCH'):gate.generate(env={'GITHUB_SHA':'0'*40})
  with self.assertRaisesRegex(ValueError,'REPO_MISMATCH'):gate.generate(env={'GITHUB_REPOSITORY':'other/repo'})
 def test_device_parser_all_or_nothing(self):
  raw='\n'.join(sum((['INSTRUMENTATION_STATUS: test='+m,'INSTRUMENTATION_STATUS_CODE: 0'] for m in runner.METHODS),[])+['INSTRUMENTATION_CODE: -1'])
  self.assertEqual(4,runner.parse(raw)['completed'])
  with self.assertRaises(DeviceGateError):runner.parse('INSTRUMENTATION_STATUS: test='+runner.METHODS[0]+'\nINSTRUMENTATION_STATUS_CODE: 0\nINSTRUMENTATION_CODE: -1')
 def test_kotlin_synthetic_file_content_and_fail_closed(self):
  if not shutil.which('kotlinc') or not shutil.which('kotlin'):self.skipTest('Kotlin unavailable')
  with tempfile.TemporaryDirectory(prefix='m24-depot-proof-') as td:
   tmp=Path(td);h=tmp/'Harness.kt';h.write_text("""import com.sdvsync.download.M24DepotFileProof
import java.io.File
import java.security.MessageDigest
fun reject(block: ()->Unit) {
 try { block(); error("fail open") }
 catch (e: IllegalStateException) { check(e.message != "fail open") }
 catch (_: IllegalArgumentException) {}
}
fun main(args:Array<String>) {
 val root=File(args[0],"stage").apply{mkdirs()}
 val content=File(root,"Content/f.bin").apply{parentFile!!.mkdirs();writeText("private fixture")}
 val hash=MessageDigest.getInstance("SHA-1").digest(content.readBytes()).joinToString(""){ "%02x".format(it) }
 val expected=mapOf("Content/f.bin" to M24DepotFileProof.FileEntry(content.length(),hash))
 check(M24DepotFileProof.verify(root,expected).files==1)
 File(root,".DepotDownloader").mkdirs()
 File(root,".DepotDownloader/depot.manifest").writeText("sdk fixture")
 check(M24DepotFileProof.verify(root,expected).files==1)
 content.writeText("tampered")
 reject { M24DepotFileProof.verify(root,expected) }
 content.writeText("private fixture")
 File(root,"unexpected").writeText("not in manifest")
 reject { M24DepotFileProof.verify(root,expected) }
 File(root,"unexpected").delete()
 reject { M24DepotFileProof.verify(root,mapOf("../outside" to expected.values.first())) }
 reject { M24DepotFileProof.verify(root,emptyMap()) }
 println("PASS_M24_MANIFEST_FILE_CROSSCHECK_NEGATIVES")
}
""")
   jar=tmp/'proof.jar'
   src=ROOT/'app/src/main/java/com/sdvsync/download/M24DepotFileProof.kt'
   build=subprocess.run(['kotlinc',str(src),str(h),'-d',str(jar)],capture_output=True,text=True,timeout=65)
   self.assertEqual(0,build.returncode,build.stderr)
   result=subprocess.run(['kotlin','-classpath',str(jar),'HarnessKt',str(tmp)],capture_output=True,text=True,timeout=20)
   self.assertEqual(0,result.returncode,result.stderr)
   self.assertIn('PASS_M24_MANIFEST_FILE_CROSSCHECK_NEGATIVES',result.stdout)
if __name__=='__main__':unittest.main()
