#!/usr/bin/env python3
"""Verify real emulator screenshot integrity, dimensions and source SHA; no OCR."""
from __future__ import annotations
import hashlib,json,struct,sys
from pathlib import Path

STAGES=('overview','files','community')
WIDTH_HEIGHT={393:(786,1704),360:(720,1600)}


def audit(out:Path,source_sha:str,run_id:str):
    assert len(source_sha)==40 and all(c in '0123456789abcdef' for c in source_sha)
    assert run_id.isdigit()
    inventory=[]
    for width,(w,h) in WIDTH_HEIGHT.items():
        for stage in STAGES:
            name=f'nex-r5-{stage}-{width}.png'
            p=out/name
            b=p.read_bytes()
            assert len(b)>5000 and b.startswith(b'\x89PNG\r\n\x1a\n')
            assert struct.unpack('>II',b[16:24])==(w,h)
            assert b.endswith(b'IEND\xaeB`\x82')
            inventory.append({'name':name,'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),
                              'width':w,'height':h,'source_sha':source_sha})
    assert len(inventory)==6
    report={'source_sha':source_sha,'run_id':run_id,'screenshots':inventory,
        'synthetic_compose_fixture':True,'real_device_qualified':False,
        'live_nexus_posts_or_media_verified':False,'release_approved':False}
    (out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('NEX_R5_API36_6_SCREENSHOTS_SOURCE_BOUND_PASS')

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: nex_r5_evidence.py <out> <sha> <run_id>')
    audit(Path(sys.argv[1]),sys.argv[2],sys.argv[3])
