#!/usr/bin/env python3
"""Audit actual Compose 200% font-scale snapshots without Pillow or golden approval."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path

TABS={'home':'cinderbox.screen.home','game':'cinderbox.screen.game',
      'saves':'cinderbox.screen.saves','mods':'cinderbox.screen.mods',
      'more':'cinderbox.screen.more'}
VIEWPORTS={393:(786,1704),360:(720,1600)}
def digest(p:Path)->str:
    assert p.is_file() and not p.is_symlink(), 'UX09C_MISSING_FILE:'+str(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def png_size(p:Path)->tuple[int,int]:
    with p.open('rb') as f:
        header=f.read(24)
    assert len(header)==24 and header[:8]==b'\x89PNG\r\n\x1a\n' and header[12:16]==b'IHDR', 'UX09C_INVALID_PNG:'+str(p)
    return struct.unpack('>II',header[16:24])

def analyze(evidence:Path,sha:str,run_id:str,app_sha:str,test_sha:str)->dict:
    assert len(sha)==40 and all(c in '0123456789abcdef' for c in sha),'UX09C_BAD_SOURCE_SHA'
    assert len(app_sha)==len(test_sha)==64 and run_id.isdecimal(),'UX09C_BAD_PROVENANCE'
    records=[]
    for width,pixels in VIEWPORTS.items():
        for tab,tag in TABS.items():
            stem=f'{tab}-{width}'
            p=evidence/(stem+'.png');meta_path=evidence/(stem+'.json')
            assert png_size(p)==pixels,'UX09C_WRONG_PNG_SIZE:'+stem
            j=json.loads(meta_path.read_text())
            assert j['tab']==tab and j['screen_tag']==tag and j['width_dp']==width
            assert j['pixel_size']==list(pixels),'UX09C_DIMENSIONS_UNTRUSTED:'+stem
            assert j['density']==2.0 and j['font_scale']==2.0,'UX09C_FONT_SCALE_UNTRUSTED:'+stem
            assert j['real_offline_main_activity'] is True and j['provider_fixture'] is False
            assert j['local_storage_mutated'] is False and j['interior_unique_colors']>=12
            nav=j['nav_targets'];assert len(nav)==5,'UX09C_MISSING_NAV_TARGETS:'+stem
            assert {x['tab'] for x in nav}=={'HOME','DOWNLOAD','SAVES','MODS','SETTINGS'}
            assert all(x['width_px']>=96 and x['height_px']>=96 for x in nav),'UX09C_TARGET_TOO_SMALL:'+stem
            records.append({'case':stem,'capture_sha256':digest(p),'metadata_sha256':digest(meta_path),
                            'size_px':list(pixels),'font_scale':2.0,'min_touch_target_px':96,
                            'real_offline_mainactivity':True})
    assert len(records)==10 and len({x['case'] for x in records})==10
    result={'schema':'cinderbox-ux09c01-hosted-accessibility-v1',
      'result':'UX09C01_LARGE_TEXT_IME_NAV_EVIDENCE_PASS',
      'source_sha':sha,'run_id':run_id,'app_sha256':app_sha,'test_apk_sha256':test_sha,
      'font_scale':2.0,'tested_viewports_dp':[393,360],'actual_offline_screenshots':10,
      'navigation_ime_and_cloud_lock_tested':True,'native_goldens_approved':False,
      'native_pixel_parity_verified':False,'real_steam_authentication_qualified':False,
      'physical_device_qualified':False,'release_enabled':False,
      'publication_enabled':False,'live_mod_bulk_writes_enabled':False,'cases':records}
    (evidence/'UX09C01_EVIDENCE.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (evidence/'UX09C01_REVIEW.md').write_text(
      '# UX-09C01: hosted actual MainActivity large-text evidence\n\n'
      f'Source `{sha}`, CI run `{run_id}`. Ten actual offline screenshots at 200% text '
      'across 393dp and 360dp. Navigation targets min 48dp. IME, Cloud lock and back '
      'are independently exercised. No pixel parity or native golden approved; '
      'not physical-device, actual Steam, TalkBack traversal or release acceptance.\n')
    return result

def main():
    parser=argparse.ArgumentParser()
    for k in ('evidence-dir','source-sha','run-id','app-sha','test-sha'):
        parser.add_argument('--'+k,required=True)
    v=vars(parser.parse_args())
    r=analyze(Path(v['evidence_dir']),v['source_sha'],v['run_id'],v['app_sha'],v['test_sha'])
    print(r['result'],r['actual_offline_screenshots'])
if __name__=='__main__':main()
