"""No-device depot handoff watchdog and safe UI progress proofs."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import m24_depot_handoff_gate as gate

ROOT=Path(__file__).resolve().parents[2]

class M24HandoffTests(unittest.TestCase):
    def test_source_contract(self):
        record=gate.validate()
        self.assertEqual(record['overall'],'PASS_M24_DEPOT_HANDOFF_SOURCE')
        self.assertFalse(record['live_download_tested'])
    def test_rejects_missing_gate(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)
            with self.assertRaisesRegex(ValueError, 'SOURCE_MISSING'):
                gate.validate(fake)
    def test_sanitized_kotlin_watchdog(self):
        if not shutil.which('kotlinc') or not shutil.which('kotlin'):
            self.skipTest('Kotlin tools unavailable')
        with tempfile.TemporaryDirectory(prefix='m24-handoff-') as d:
            scratch=Path(d)
            src=ROOT/'app/src/main/java/com/sdvsync/download/M24DepotHandoffPolicy.kt'
            harness=scratch/'Harness.kt'
            harness.write_text('import com.sdvsync.download.M24DepotHandoffPolicy as P\nfun main() {\n check(P.safePhase("Downloading manifest for depot 413151") == "Fetching Steam depot manifest…")\n check(P.safePhase("Allocating file: /secret/path") == "Allocating Steam depot files…")\n check(P.safePhase("Validating: /private/steam.dat") == "Checking existing Steam depot chunks…")\n check(P.safePhase("access_token=VERY_PRIVATE_SECRET") == null)\n check(P.failureCode(239999,0,0,false,false) == null)\n check(P.failureCode(240000,0,0,false,false) == "STEAM_DEPOT_FIRST_CONTENT_TIMEOUT")\n check(P.failureCode(500000,0,200001,true,false) == null)\n check(P.failureCode(500001,0,200001,true,false) == "STEAM_DEPOT_CONTENT_STALLED")\n check(P.failureCode(1,0,0,false,true) == "STEAM_DEPOT_REPORTED_FAILURE")\n println("PASS_M24_HANDOFF_WATCHDOG_NEGATIVES")\n}\n')
            jar=scratch/'proof.jar'
            cp=subprocess.run(['kotlinc',str(src),str(harness),'-d',str(jar)],capture_output=True,text=True,timeout=90)
            self.assertEqual(cp.returncode,0,cp.stderr)
            run=subprocess.run(['kotlin','-classpath',str(jar),'HarnessKt'],capture_output=True,text=True,timeout=25)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('PASS_M24_HANDOFF_WATCHDOG_NEGATIVES',run.stdout)

if __name__=='__main__': unittest.main()
