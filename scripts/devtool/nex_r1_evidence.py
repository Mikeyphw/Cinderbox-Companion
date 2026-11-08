#!/usr/bin/env python3
"""Strict hosted evidence decoder; never accepts synthetic fixture images as real acceptance."""
import hashlib,json,pathlib,sys
from PIL import Image, ImageStat

def check(folder,sha,run):
    base=pathlib.Path(folder)
    expected={f'nex-r1-{stage}-{width}.png' for stage in ('mods','filter') for width in (360,393)}
    found={p.name for p in base.glob('*.png')}
    assert found==expected,f'NEX_R1_WRONG_SCREENSHOT_SET:{found}'
    items=[]
    for name in sorted(expected):
        raw=(base/name).read_bytes()
        assert raw.startswith(b'\x89PNG\r\n\x1a\n'),f'NEX_R1_BAD_PNG:{name}'
        with Image.open(base/name) as image:
            image.load()
            w,h=image.size
            assert (w,h) in ((720,1600),(786,1704)),f'NEX_R1_WRONG_VIEWPORT:{name}'
            assert w//2==int(name.split('-')[-1][:-4]),f'NEX_R1_WRONG_DENSITY:{name}'
            rgb=image.convert('RGB')
            colors=len(set(rgb.resize((80,120)).getdata()))
            assert colors>30,f'NEX_R1_BLANK:{name}:{colors}'
        items.append(dict(name=name,sha256=hashlib.sha256(raw).hexdigest(),pixels=[w,h],colors=colors))
    receipt=dict(schema=1,source_sha=sha,github_run_id=run,emulator_api=36,
      font_percent=100,source='real-offline-MainActivity',images=items,
      device_qualification=False,native_goldens=False,steam_auth=False,mod_writes=False)
    (base/'NEX_R1_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('NEX_R1_HOSTED_FOUR_REAL_SCREENSHOTS:'+str(len(items)))

if __name__=='__main__':check(*sys.argv[1:4])
