#!/usr/bin/env python3
"""Validate and seal allowlisted source-bound, private hosted emulator screenshots."""
import hashlib,json,struct,sys
from pathlib import Path


def verify(folder: Path, sha: str, runid: str) -> dict:
    assert len(sha)==40 and all(x in '0123456789abcdef' for x in sha)
    assert runid.isdecimal()
    expected = {f'{prefix}-{stage}-{width}.png'
        for prefix, stages in [('main', ['mods','filter']),
                               ('fixture',['overview','files','missing'])]
        for stage in stages for width in (360,393)}
    assert {p.name for p in folder.glob('*.png')} == expected, 'NEX_R2_SCREENSHOT_INVENTORY_REFUSED'
    evidence=[]
    for name in sorted(expected):
        raw=(folder/name).read_bytes()
        assert len(raw)>=4000 and raw[:8]==b'\x89PNG\r\n\x1a\n', 'NEX_R2_INVALID_PNG'
        w,h=struct.unpack('>II',raw[16:24]);width=int(name[:-4].split('-')[-1])
        assert w==width*2 and h>=900 and h<=1900, 'NEX_R2_VIEWPORT_REFUSED'
        evidence.append({'name':name,'width_px':w,'height_px':h,'sha256':hashlib.sha256(raw).hexdigest(),
                         'synthetic_fixture': name.startswith('fixture-')})
    return {'schema_version':1,'source_sha':sha,'run_id':runid,
        'real_main_activity_discovery':True,'detail_is_synthetic_fixture':True,
        'real_nexus_metadata_qualified':False,'nexus_schema_live_qualified':False,
        'physical_device_qualified':False,'release_qualified':False,
        'publication_allowed':False,'screen_captures':evidence}

if __name__=='__main__':
    assert len(sys.argv)==4
    root=Path(sys.argv[1]); evidence=verify(root,sys.argv[2],sys.argv[3]);
    (root/'NEX_R2_HOSTED_EVIDENCE.json').write_text(json.dumps(evidence,sort_keys=True,indent=2)+'\n')
    print('NEX_R2_PRIVATE_SCREENSHOT_EVIDENCE_PASS',len(evidence['screen_captures']))
