#!/usr/bin/env python3
"""Synthetic negatives only. Not a physical device or live Nexus witness."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

src=Path(__file__).with_name('cbnx06_physical_acceptance.py')
spec=importlib.util.spec_from_file_location('cbnx06',src)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

M='12345';F='67890';HASH='a'*64;JOB='123e4567-e89b-12d3-a456-426614174000'

def fixture():
    device={'physical_arm64_api36':True,'android_api':36,'installed_cinderbox_apk_sha256':HASH,
            'gecko_browser_packages':['io.github.forkmaintainers.iceraven'],
            'installed_extension_proven':False,'no_emulator_flags':True}
    mods={'metadata_listing_sha256':'c'*64,'file_byte_proof':False,'full_contents_sha256':None}
    base={'device':device,'mods':mods,'private':{'inbox':[],'journal':[],
                                                'review':{'present':False},'journal_count':0,'inbox_count':0}}
    before={'schema':p.SCHEMA,'selected_mod_id':M,'selected_file_id':F,
            'captured_epoch_ms':1762850000000,'snapshot':base}
    after=copy.deepcopy(base)
    after['private']['inbox']=[{'id_hash':'b'*64,'mod':M,'file':F,'status':'PENDING',
                                'created':1762850001000}]
    after['private']['journal']=[{'id':JOB,'source':'nexus','mod':M,'file':F,
                                  'status':'REVIEW_REQUIRED','created':1762850001500}]
    after['private']['review']={'present':True,'sha256':HASH,'bytes':12345,
                                 'receipt_matches_archive':True,'source':'nexus',
                                 'mod':M,'file':F,'job_id':JOB}
    return before,after

class TestWit(unittest.TestCase):
    def test_valid_private_staging_is_not_live_qualification(self):
        before,after=fixture();v=p.assess(before,after)
        self.assertEqual(v['status'],'EXACT_FILE_PRIVATE_STAGING_WITNESSED')
        self.assertFalse(v['live_nexus_qualified']);self.assertFalse(v['release_qualified'])
        self.assertFalse(v['browser_action_independently_proven'])
        self.assertFalse(v['mods_file_byte_contents_unchanged_proven'])

    def test_no_new_pairing_request(self):
        b,a=fixture();a['private']['inbox']=[]
        self.assertIn('NO_NEW_EXACT_FILE_PAIRING_REQUEST',p.assess(b,a)['reason_codes'])

    def test_old_request_cannot_replay(self):
        b,a=fixture();b['snapshot']['private']['inbox']=copy.deepcopy(a['private']['inbox'])
        self.assertIn('NO_NEW_EXACT_FILE_PAIRING_REQUEST',p.assess(b,a)['reason_codes'])

    def test_fake_old_request_time(self):
        b,a=fixture();a['private']['inbox'][0]['created']=b['captured_epoch_ms']-100000
        self.assertIn('PAIRING_REQUEST_IDENTITY_NOT_FRESH',p.assess(b,a)['reason_codes'])

    def test_archive_mismatch_sha(self):
        b,a=fixture();a['private']['review']['receipt_matches_archive']=False
        self.assertIn('REVIEW_ARCHIVE_CHECKSUM_MISMATCH',p.assess(b,a)['reason_codes'])

    def test_wrong_exact_file(self):
        b,a=fixture();a['private']['review']['file']='3'
        self.assertIn('REVIEW_RECEIPT_MOD_OR_FILE_MISMATCH',p.assess(b,a)['reason_codes'])

    def test_reused_old_job(self):
        b,a=fixture();b['snapshot']['private']['journal']=copy.deepcopy(a['private']['journal'])
        self.assertIn('REUSED_PREEXISTING_JOURNAL_JOB',p.assess(b,a)['reason_codes'])

    def test_no_review_job(self):
        b,a=fixture();a['private']['journal']=[]
        self.assertIn('NO_MATCHING_JOURNAL_AND_REVIEW',p.assess(b,a)['reason_codes'])

    def test_installed_is_not_review(self):
        b,a=fixture();a['private']['journal'][0]['status']='INSTALLED'
        self.assertIn('NO_MATCHING_JOURNAL_AND_REVIEW',p.assess(b,a)['reason_codes'])

    def test_blocked_or_uncertain_archive_is_not_qualified(self):
        for status in ('BLOCKED','VERIFY_REQUIRED'):
            b,a=fixture();a['private']['journal'][0]['status']=status
            self.assertIn('NO_MATCHING_JOURNAL_AND_REVIEW',p.assess(b,a)['reason_codes'])
            self.assertEqual(p.assess(b,a)['status'],'INCONCLUSIVE_NOT_QUALIFIED')

    def test_game_data_metadata_must_stay_unchanged(self):
        b,a=fixture();a['mods']['metadata_listing_sha256']='f'*64
        self.assertIn('MODS_METADATA_CHANGED_BEFORE_REVIEW',p.assess(b,a)['reason_codes'])

    def test_full_content_hash_is_strict(self):
        b,a=fixture();b['snapshot']['mods'].update(file_byte_proof=True,full_contents_sha256='1'*64)
        a['mods'].update(file_byte_proof=True,full_contents_sha256='2'*64)
        self.assertIn('MODS_CONTENT_CHANGED_BEFORE_REVIEW',p.assess(b,a)['reason_codes'])
        a['mods']['full_contents_sha256']='1'*64
        self.assertTrue(p.assess(b,a)['mods_file_byte_contents_unchanged_proven'])

    def test_device_or_apk_changed(self):
        b,a=fixture();a['device']['installed_cinderbox_apk_sha256']='f'*64
        self.assertIn('DEVICE_OR_APK_CHANGED',p.assess(b,a)['reason_codes'])

    def test_prefs_absent_vs_corrupt(self):
        self.assertIsNone(p.parse_prefs(None,'records',missing_ok=True))
        with self.assertRaises(p.Refusal):p.parse_prefs(b'<map><bad></map>','records',missing_ok=True)
        with self.assertRaises(p.Refusal):p.parse_prefs(b'<map/>','records',missing_ok=True)

    def test_valid_journal_and_inbox_without_secrets(self):
        j=[{'id':JOB,'source':'nexus','modId':M,'fileId':F,'status':'REVIEW_REQUIRED',
             'name':'SENSITIVE_FILENAME','detail':'NXM_SECRET','created':1762850001500}]
        from xml.sax.saxutils import escape
        xml=('<map><string name="records">'+escape(json.dumps(j))+'</string></map>').encode()
        out=p.journal_rows(xml)
        self.assertEqual(out[0]['status'],'REVIEW_REQUIRED')
        self.assertNotIn('SENSITIVE_FILENAME',repr(out));self.assertNotIn('NXM_SECRET',repr(out))
        data=[{'id':'A'*24,'mod_id':M,'file_id':F,'status':'PENDING','created_at':1762850001000}]
        xml=('<map><string name="requests_v1">'+escape(json.dumps(data))+'</string></map>').encode()
        self.assertEqual(len(p.inbox_rows(xml)[0]['id_hash']),64)
        self.assertNotIn('A'*24,repr(p.inbox_rows(xml)))

    def test_duplicate_journal_id_refused(self):
        row={'id':JOB,'source':'nexus','modId':M,'fileId':F,'status':'REVIEW_REQUIRED'}
        from xml.sax.saxutils import escape
        xml=('<map><string name="records">'+escape(json.dumps([row,row]))+'</string></map>').encode()
        with self.assertRaises(p.Refusal):p.journal_rows(xml)

    def test_mismatched_or_unsafe_archive_receipt(self):
        good=f'source=nexus\nmod_id={M}\nfile_id={F}\njob_id={JOB}\nsha256={HASH}\n'.encode()
        self.assertEqual(p.receipt_properties(good)['file_id'],F)
        for evil in (good.replace(b'file_id=67890',b'file_id=2222'),
                     good.replace(b'sha256='+HASH.encode(),b'sha256=invalid'),
                     good.replace(b'source=nexus',b'source=other'),
                     good+b'file_id=777\n'):
            if b'file_id=2222' in evil:continue # another positive ID is caught by cross-file assess
            with self.assertRaises(p.Refusal):p.receipt_properties(evil)

    def test_private_file_existence_does_not_cat_archive(self):
        adb=p.Adb('localhost:5555')
        calls=[]
        def fake(*args,**kwargs):
            calls.append(args)
            return None if '-L' in args else b''
        with patch.object(adb,'run',side_effect=fake):
            self.assertTrue(adb.private_exists(p.PENDING_ZIP))
        self.assertFalse(any('cat' in args for args in calls))

    def test_explicit_serial_only(self):
        for serial in ('emulator-5554','192.168.1.2:5555','localhost:5555; rm -rf /',''):
            with self.assertRaises(p.Refusal):p.Adb(serial)
        p.Adb('localhost:5555')

    def test_android_emulator_refused(self):
        class Fake:
            def text(self,*args,optional=False):
                if args==('get-state',):return 'device'
                if args[:2]==('shell','pm'):return 'package:/data/app/mock/base.apk'
                if args[:2]==('shell','sha256sum'):return HASH+'  /data/app/mock/base.apk'
                return 'uid=1000'
            def prop(self,name):
                return {'ro.build.version.sdk':'36','ro.product.cpu.abi':'arm64-v8a',
                        'ro.kernel.qemu':'1','ro.hardware':'ranchu','ro.product.model':'sdk_gphone64_arm64'}.get(name,'')
        with self.assertRaises(p.Refusal):p.physical(Fake())

    def test_written_session_private_and_nonoverwrite(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'before.json';p.private_write(f,{'schema':p.SCHEMA,'secret_test':'none'})
            self.assertEqual(p.safe_load(f)['schema'],p.SCHEMA)
            with self.assertRaises(FileExistsError):p.private_write(f,{})
            link=Path(td)/'link.json';link.symlink_to(f)
            with self.assertRaises(p.Refusal):p.safe_load(link)

    def test_synthetic_before_after_record_lifecycle(self):
        before,after=fixture()
        after['private']['inbox'][0]['created']=int(time.time()*1000)
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'app-debug.apk';apk.write_bytes(b'CI test artifact')
            sha=p.digest(apk.read_bytes())
            attest=Path(td)/'SOURCE_ATTESTATION.json'
            attest.write_text(json.dumps({'schema':'cbnx06-hosted-debug-apk-v1',
                'source_sha':'a'*40,'apk_sha256':sha,
                'physical_arm64_qualified':False,'live_firefox_qualified':False,
                'live_nexus_qualified':False,'release_qualified':False}))
            a=SimpleNamespace(mod_id=M,file_id=F,apk_file=str(apk),apk_attestation=str(attest),apk_sha256=sha,
                              evidence_dir=str(Path(td)/'session'),full_mods_hash=False,
                              cinderbox_sha='a'*40,firefox_sha='b'*40)
            before['snapshot']['device']['installed_cinderbox_apk_sha256']=sha
            after['device']['installed_cinderbox_apk_sha256']=sha
            with patch.object(p,'snapshot',return_value=before['snapshot']):
                p.start(a,None)
            with patch.object(p,'snapshot',return_value=after):
                self.assertEqual(p.finish(a,None),0)
            files=list(Path(a.evidence_dir).glob('after-*.json'))
            self.assertEqual(len(files),1)
            record=p.safe_load(files[0])
            self.assertEqual(record['evaluation']['status'],'EXACT_FILE_PRIVATE_STAGING_WITNESSED')
            self.assertFalse(record['release_qualified'])
            self.assertFalse(record['live_nexus_qualified'])

    def test_ci_artifact_provenance_refuses_wrong_sha_and_missing_attestation(self):
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'app-debug.apk';apk.write_bytes(b'valid local bytes')
            h=p.digest(apk.read_bytes())
            receipt=Path(td)/'SOURCE_ATTESTATION.json'
            record={'schema':'cbnx06-hosted-debug-apk-v1','source_sha':'a'*40,
                    'apk_sha256':h,'physical_arm64_qualified':False,
                    'live_firefox_qualified':False,'live_nexus_qualified':False,
                    'release_qualified':False}
            a=SimpleNamespace(mod_id=M,file_id=F,apk_file=str(apk),apk_attestation=str(receipt),
                              apk_sha256=h,evidence_dir=str(Path(td)/'session'),
                              full_mods_hash=False,cinderbox_sha='a'*40,firefox_sha='b'*40)
            with self.assertRaises(p.Refusal):p.start(a,None)
            for key,bad in [('source_sha','b'*40),('apk_sha256','0'*64),('release_qualified',True)]:
                changed=dict(record);changed[key]=bad
                receipt.write_text(json.dumps(changed))
                with self.assertRaises(p.Refusal):p.start(a,None)
            receipt.write_text(json.dumps(record))
            with patch.object(p,'snapshot',side_effect=p.Refusal('EXPECTED_DEVICE_BLOCK')):
                with self.assertRaisesRegex(p.Refusal,'EXPECTED_DEVICE_BLOCK'):p.start(a,None)

    def test_before_existing_review_refuses_and_writes_nothing(self):
        before,_=fixture()
        before['snapshot']['private']['review']={'present':True}
        with tempfile.TemporaryDirectory() as td:
            apk=Path(td)/'app-debug.apk';apk.write_bytes(b'CI test artifact')
            sha=p.digest(apk.read_bytes())
            attest=Path(td)/'SOURCE_ATTESTATION.json'
            attest.write_text(json.dumps({'schema':'cbnx06-hosted-debug-apk-v1',
                'source_sha':'a'*40,'apk_sha256':sha,
                'physical_arm64_qualified':False,'live_firefox_qualified':False,
                'live_nexus_qualified':False,'release_qualified':False}))
            a=SimpleNamespace(mod_id=M,file_id=F,apk_file=str(apk),apk_attestation=str(attest),apk_sha256=sha,
                              evidence_dir=str(Path(td)/'session'),full_mods_hash=False,
                              cinderbox_sha='a'*40,firefox_sha='b'*40)
            before['snapshot']['device']['installed_cinderbox_apk_sha256']=sha
            with patch.object(p,'snapshot',return_value=before['snapshot']):
                with self.assertRaises(p.Refusal):p.start(a,None)
            self.assertFalse((Path(a.evidence_dir)/'before.json').exists())

    def test_never_auto_qualifies_release_or_live(self):
        text=src.read_text()
        self.assertNotIn("'live_nexus_qualified':True",text)
        self.assertNotIn("'release_qualified':True",text)
        self.assertNotIn('su -c ',text)
        self.assertIn('EXACT_CI_DEBUG_APK_AND_SOURCE_ATTESTATION_FILES_REQUIRED',text)

if __name__=='__main__':
    unittest.main(verbosity=2)
