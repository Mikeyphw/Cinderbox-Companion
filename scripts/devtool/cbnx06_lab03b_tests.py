#!/usr/bin/env python3
"""LAB03B negative cases; synthetic APK/XPI bytes only, never ADB/network."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from cbnx06_lab03b_readonly import (LAB, GECKO, PROD_GECKO, Refused,
    validate_artifacts, parse_inbox, witnessed, assess_after, sha_file,
    physical_snapshot, Device, SCHEMA)

ANDROID = 'a'*40
BROWSER = 'b'*40

class MockDevice:
    def __init__(self, **changes):
        self.props={'ro.build.version.sdk':'36','ro.product.cpu.abi':'arm64-v8a',
          'ro.kernel.qemu':'','ro.boot.qemu':'','ro.hardware':'mt6785',
          'ro.product.model':'AndroidDevice','ro.build.fingerprint':'vendor/real'}
        self.props.update(changes)
        self.paths={'com.sdvsync':'/data/app/~~test/com.sdvsync-a/base.apk',
                    LAB:'/data/app/~~test/com.sdvsync.cbnx06lab-a/base.apk',
                    'io.github.forkmaintainers.iceraven':'/data/app/~~test/iceraven-a/base.apk'}
        self.hashes={p:'a'*64 if pkg=='com.sdvsync' else 'b'*64 for pkg,p in self.paths.items()}
    def txt(self,*args,optional=False):return 'device'
    def prop(self,k):return self.props.get(k,'')
    def package_apk(self,p,required=True):return self.paths.get(p)
    def package_sha(self,p):return self.hashes[p]

class Lab03bTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='cbnx-lab03b-')
        self.addCleanup(self.tmp.cleanup)
        r=Path(self.tmp.name)
        self.apk=r/'app-cbnxlab-debug.apk';self.apk.write_bytes(b'APP'*40000)
        self.xpi=r/'stardew-lab.xpi'
        with ZipFile(self.xpi,'w') as z:
            z.writestr('manifest.json',json.dumps({'name':'Stardew Cinderbox LAB',
                'browser_specific_settings':{'gecko':{'id':GECKO}}}))
            z.writestr('cbnx03-background.js',"const BASE = 'http://127.0.0.1:38472'")
            z.writestr('README.txt','fixture'*200)
        from cbnx06_lab03b_readonly import sha_bytes
        self.lab_att=r/'LAB_ARTIFACT_ATTESTATION.json'
        self.browser_att=r/'LAB02C_ARTIFACT_ATTESTATION.json'
        self.lab={ 'schema':'cbnx06-full-cinderbox-lab-v1', 'source_sha':ANDROID,
            'application_id':LAB,'lab_isolated_build':True,'source_attested':True,
            'physical_qualified':False,'apk_sha256':sha_file(self.apk),
            'certificate_sha256':'1'*64 }
        with ZipFile(self.xpi) as z:
            xpi_file_sha256={n:sha_bytes(z.read(n)) for n in z.namelist()}
        self.browser={'schema':'cbnx06-lab02c-isolated-unsigned-xpi-v1',
            'browser_source_sha':BROWSER,'extension_id':GECKO,
            'production_extension_id':PROD_GECKO,'android_lab_application_id':LAB,
            'android_lab_port':38472,'production_port':38471,
            'signed':False,'browser_installed':False,'physical_qualified':False,
            'xpi_sha256':sha_file(self.xpi),'xpi_file_sha256':xpi_file_sha256}
        self.flush()
    def flush(self):
        self.lab_att.write_text(json.dumps(self.lab))
        self.browser_att.write_text(json.dumps(self.browser))
    def attest(self):return validate_artifacts(self.apk,self.lab_att,self.xpi,
                                             self.browser_att,ANDROID,BROWSER)
    def test_positive_artifact_inspection_never_claims_installed(self):
        d=self.attest();self.assertFalse(d['xpi_installed_verified']);self.assertFalse(d['xpi_signed'])
    def test_wrong_app_id_refused(self):
        self.lab['application_id']='com.sdvsync';self.flush()
        with self.assertRaises(Refused):self.attest()
    def test_wrong_source_refused(self):
        with self.assertRaises(Refused):validate_artifacts(self.apk,self.lab_att,self.xpi,
            self.browser_att,'f'*40,BROWSER)
    def test_wrong_cert_refused(self):
        self.lab['certificate_sha256']='';self.flush()
        with self.assertRaises(Refused):self.attest()
    def test_apk_changed_refused(self):
        self.apk.write_bytes(self.apk.read_bytes()+b'x')
        with self.assertRaises(Refused):self.attest()
    def test_signed_claim_not_accepted_from_unsigned_artifact(self):
        self.browser['signed']=True;self.flush()
        with self.assertRaises(Refused):self.attest()
    def test_production_gecko_id_refused(self):
        self.browser['extension_id']=PROD_GECKO;self.flush()
        with self.assertRaises(Refused):self.attest()
    def test_production_port_refused(self):
        self.browser['android_lab_port']=38471;self.flush()
        with self.assertRaises(Refused):self.attest()
    def test_xpi_embedded_production_port_refused(self):
        with ZipFile(self.xpi,'w') as z:
            z.writestr('manifest.json',json.dumps({'name':'Stardew Cinderbox LAB',
                'browser_specific_settings':{'gecko':{'id':GECKO}}}))
            z.writestr('cbnx03-background.js',"const BASE = 'http://127.0.0.1:38471'")
        self.browser['xpi_sha256']=sha_file(self.xpi)
        with ZipFile(self.xpi) as z:
            from cbnx06_lab03b_readonly import sha_bytes
            self.browser['xpi_file_sha256']={n:sha_bytes(z.read(n)) for n in z.namelist()}
        self.flush()
        with self.assertRaises(Refused):self.attest()
    def test_real_arm64_accepts_package_identity(self):
        dev=MockDevice();p=physical_snapshot(dev,'b'*64)
        self.assertTrue(p['lab_apk_exact_bytes_match']);self.assertFalse(p['production_game_unchanged_proven'])
    def test_emulator_refused(self):
        with self.assertRaises(Refused):physical_snapshot(MockDevice(**{'ro.kernel.qemu':'1'}))
    def test_wrong_lab_bytes_refused(self):
        with self.assertRaises(Refused):physical_snapshot(MockDevice(),'c'*64)
    def test_lab_missing_refused(self):
        dev=MockDevice();dev.paths.pop(LAB)
        with self.assertRaises(Refused):physical_snapshot(dev,'b'*64)
    def test_browser_not_present_refused(self):
        dev=MockDevice();dev.paths.pop('io.github.forkmaintainers.iceraven')
        with self.assertRaises(Refused):physical_snapshot(dev,'b'*64)
    def test_inbox_invalid_id_refused(self):
        raw=b'<map><string name="requests_v1">[{"id":"../evil","mod_id":"123","file_id":"456","status":"PENDING","created_at":123}]</string></map>'
        with self.assertRaises(Refused):parse_inbox(raw)
    def test_inbox_xml_dtd_refused(self):
        with self.assertRaises(Refused):parse_inbox(b'<!DOCTYPE map><map/>')
    def test_inbox_rows_are_only_bounded_and_redacted(self):
        item={'id':'A'*24,'mod_id':'123','file_id':'456','status':'PENDING','created_at':123}
        b=json.dumps([item]).replace('&','&amp;')
        rows=parse_inbox(('<map><string name="requests_v1">'+b+'</string></map>').encode())
        w=witnessed(rows,'deadbeef','123','456')
        self.assertEqual(len(w['matching_request_hashes']),1)
        self.assertNotIn('123',json.dumps(w));self.assertNotIn('AAAAAA',json.dumps(w))
    def test_fresh_exact_inbox_is_observation_not_browser_proof(self):
        salt='deadbeef';old={'schema':SCHEMA,'stage':'before',
            'salt':salt, 'selected_identity_hash':__import__('hashlib').sha256((salt+':123:456').encode()).hexdigest(),
            'artifacts':{'source_sha':ANDROID,'browser_source_sha':BROWSER},
            'snapshot':{'physical_device':True,'production_apk_sha256':'a'*64,
                'lab_apk_sha256':'b'*64,'browser_packages':['iceraven']},
            'inbox':witnessed([],'deadbeef','123','456')}
        actual={'physical_device':True,'lab_apk_exact_bytes_match':True,
                'production_apk_sha256':'a'*64,'lab_apk_sha256':'b'*64,
                'browser_packages':['iceraven']}
        w=witnessed([{'id':'B'*24,'mod_id':'123','file_id':'456',
                     'created_at':int(__import__('time').time()*1000)}],salt,'123','456',0)
        result=assess_after(old,actual,w,'123','456')
        self.assertTrue(result['new_exact_private_inbox_request_observed'])
        self.assertFalse(result['live_browser_pairing_proven'])
        self.assertFalse(result['release_qualified'])
        with self.assertRaises(Refused):assess_after(old,{**actual,'production_apk_sha256':'c'*64},w,'123','456')
    def test_stale_newly_visible_row_cannot_be_passed_as_recent(self):
        salt='abc'; from cbnx06_lab03b_readonly import sha_bytes
        old={'schema':SCHEMA,'stage':'before','salt':salt,
            'selected_identity_hash':sha_bytes((salt+':123:456').encode()),
            'artifacts':{'source_sha':ANDROID,'browser_source_sha':BROWSER},
            'snapshot':{'physical_device':True,'production_apk_sha256':'a'*64,
              'lab_apk_sha256':'b'*64,'browser_packages':['iceraven']},
            'inbox':witnessed([],salt,'123','456')}
        snap={**old['snapshot'],'lab_apk_exact_bytes_match':True}
        recent=witnessed([{'id':'A'*24,'mod_id':'123','file_id':'456','created_at':100}],
                         salt,'123','456',since_ms=1000000)
        r=assess_after(old,snap,recent,'123','456')
        self.assertFalse(r['new_exact_private_inbox_request_observed'])
    def test_no_fake_success_without_fresh_event(self):
        salt='abc';from cbnx06_lab03b_readonly import sha_bytes
        old={'schema':SCHEMA,'stage':'before','salt':salt,
            'selected_identity_hash':sha_bytes((salt+':123:456').encode()),
            'artifacts':{'source_sha':ANDROID,'browser_source_sha':BROWSER},
            'snapshot':{'physical_device':True,'production_apk_sha256':'a'*64,
              'lab_apk_sha256':'b'*64,'browser_packages':['iceraven']},
            'inbox':witnessed([],'abc','123','456')}
        snap={**old['snapshot'],'lab_apk_exact_bytes_match':True}
        r=assess_after(old,snap,witnessed([],'abc','123','456'),'123','456')
        self.assertFalse(r['new_exact_private_inbox_request_observed'])
    def test_explicit_adb_loopback_serial_required(self):
        with self.assertRaises(Refused):Device('emulator-5554')
        with self.assertRaises(Refused):Device('192.168.1.10:5555')

if __name__=='__main__':unittest.main(verbosity=2)
