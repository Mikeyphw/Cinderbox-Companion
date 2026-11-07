#!/usr/bin/env python3
"""Fail-closed hosted UX09D02 screenshot audit. Run on GitHub with Pillow 11.3.0.

All statuses are diagnostic only: no pixel parity, credentials, physical device,
privileged writes, publication or release acceptance.
"""
from __future__ import annotations
import argparse,hashlib,json,pathlib,sys

CASES=('home','game','advanced-mods','steam-login','operation-center')
VIEWPORTS={393:(786,1704),360:(720,1600)}


def verify(evidence:pathlib.Path, source:str, run_id:str):
    from PIL import Image
    screens=[]
    for width,(px,py) in VIEWPORTS.items():
        for case in CASES:
            stem=f'ux09d02-{case}-{width}'
            png=evidence/(stem+'.png')
            meta=evidence/(stem+'.json')
            if not png.is_file() or not meta.is_file():
                raise ValueError(f'UX09D02_MISSING_EVIDENCE:{stem}')
            raw=png.read_bytes()
            if not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw)<4096:
                raise ValueError(f'UX09D02_BAD_PNG:{stem}')
            with Image.open(png) as image:
                image.verify()  # PNG chunk and data integrity
            with Image.open(png) as image:
                image.load()    # image decode; not only header integrity
                if image.size != (px,py):
                    raise ValueError(f'UX09D02_WRONG_PIXELS:{stem}:{image.size}')
                rgb=image.convert('RGB')
                # Sample across a wide content rectangle. Avoid central-line false blanks.
                colors={rgb.getpixel((x,y)) for y in range(py//4,py*3//4,29)
                        for x in range(px//8,px*7//8,29)}
                if len(colors)<8:
                    raise ValueError(f'UX09D02_BLANK_SCREEN:{stem}:{len(colors)}')
                # Actual screenshot evidence: bright system status symbols on dark top.
                # This does not prove contrast on the physical Android 16 handset.
                light_count=sum(1 for y in range(7,min(py//24,75))
                                for x in range(px*7//10,px-15,2)
                                if min(rgb.getpixel((x,y)))>=160)
                if light_count<20:
                    raise ValueError(f'UX09D02_DARK_STATUS_ICONS:{stem}:{light_count}')
            receipt=json.loads(meta.read_text())
            expected={'case':case,'source':'real-offline-MainActivity','font_percent':100,
                      'status_icons_light_requested':True,'steam_auth_attempted':False,
                      'privileged_write_performed':False,'physical_device_qualified':False,
                      'native_goldens_approved':False}
            if any(receipt.get(key)!=value for key,value in expected.items()):
                raise ValueError(f'UX09D02_BAD_RECEIPT:{stem}')
            if receipt.get('viewport')!=[px,py]:
                raise ValueError(f'UX09D02_BAD_VIEWPORT_RECEIPT:{stem}')
            screens.append({'case':case,'width_dp':width,'sha256':hashlib.sha256(raw).hexdigest(),
                            'decoded_nonflat_colors':len(colors),'light_status_sample_count':light_count})
    summary={'schema':'ux09d02-hosted-v1','result':'UX09D02_TEN_REAL_ROUTE_SCREENSHOT_CANDIDATES',
             'source_commit':source,'github_run_id':run_id,'screens':screens,
             'native_goldens_approved':False,'physical_device_qualified':False,
             'steam_auth_qualified':False,'privileged_writes_qualified':False,
             'release_qualified':False,'publication_enabled':False,
             'approved_dark_reference_unchanged':True}
    (evidence/'UX09D02_EVIDENCE.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=pathlib.Path,required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    if not (len(args.source)==40 and all(c in '0123456789abcdef' for c in args.source)):
        raise SystemExit('UX09D02_BAD_SOURCE_SHA')
    if not args.run_id.isdigit():
        raise SystemExit('UX09D02_BAD_RUN_ID')
    try:
        result=verify(args.evidence,args.source,args.run_id)
    except (OSError,ValueError,ImportError) as e:
        raise SystemExit(str(e))
    print(result['result'],len(result['screens']))

if __name__=='__main__':
    main()
