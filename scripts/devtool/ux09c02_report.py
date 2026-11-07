#!/usr/bin/env python3
"""Zero-dependency 12-case actual offline UI evidence receipt; never bless native goldens."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
CASES=('home','steam','mods')
SIZES={393:(786,1704),360:(720,1600)}
SCALES=(100,200)
def sha(p):
    assert p.is_file() and not p.is_symlink(),'UX09C02_MISSING_FILE:'+str(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()
def analyze(root:Path, source:str,run_id:str):
    assert len(source)==40 and all(c in '0123456789abcdef' for c in source)
    assert run_id.isdecimal()
    items=[]
    for w,pixels in SIZES.items():
        for scale in SCALES:
            for case in CASES:
                stem=f'ux09c02-{case}-{w}-{scale}'
                png=root/(stem+'.png');json_file=root/(stem+'.json')
                with png.open('rb') as stream: header=stream.read(24)
                assert len(header)==24 and header[:8]==b'\x89PNG\r\n\x1a\n' and header[12:16]==b'IHDR','UX09C02_BAD_PNG:'+stem
                assert struct.unpack('>II',header[16:24])==pixels,'UX09C02_WRONG_SIZE:'+stem
                md=json.loads(json_file.read_text())
                assert md['case']==case and md['pixel_size']==list(pixels),'UX09C02_BAD_META:'+stem
                assert md['font_percent']==scale and md['content_top_px']>=32,'UX09C02_STATUS_OVERLAP:'+stem
                assert md['real_offline_main_activity'] is True
                assert md['steam_auth_performed'] is False and md['mod_install_performed'] is False
                assert md['physical_device_qualified'] is False and md['interior_unique_colors']>=10
                items.append({'case':case,'viewport_dp':w,'font_percent':scale,'png_sha256':sha(png),
                              'json_sha256':sha(json_file),'status_safe_top_px':md['content_top_px']})
    assert len(items)==12 and len(set((x['case'],x['viewport_dp'],x['font_percent']) for x in items))==12
    result={'result':'UX09C02_HOSTED_REAL_UI_EVIDENCE_PASS','source_sha':source,'run_id':run_id,
      'real_offline_screenshots':12,'cases':items,'steam_auth_qualified':False,
      'native_goldens_approved':False,'physical_device_qualified':False,
      'release_enabled':False,'privileged_writes_qualified':False}
    (root/'UX09C02_EVIDENCE.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True)
    parser.add_argument('--source',required=True);parser.add_argument('--run-id',required=True)
    a=parser.parse_args();print(analyze(Path(a.evidence),a.source,a.run_id)['result'])
