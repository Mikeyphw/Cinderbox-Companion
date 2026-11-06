#!/usr/bin/env python3
"""Compare a hosted *synthetic* Compose capture to the matching approved HTML viewport.

This is a bounded cross-renderer visual-drift gate and geometry diagnostic, not
native golden pixel parity, production device qualification, or proof that a
specific downloaded mod is compatible with Android.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from PIL import Image, ImageChops, ImageStat


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--actual',required=True,type=Path)
    parser.add_argument('--reference',required=True,type=Path)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--source-sha',required=True)
    parser.add_argument('--expected-width',required=True,type=int)
    parser.add_argument('--expected-height',required=True,type=int)
    args=parser.parse_args()
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    receipt={
        'schema':2,'source_sha':args.source_sha,
        'hosted_emulator_only':True,'synthetic_fixture':True,
        'physical_device_qualified':False,'release_qualified':False,
        'pixel_parity_verified':False,'comparison_pass':False,
        'comparison_kind':'cross_renderer_viewport_matched_diagnostic',
        'target_viewport':[args.expected_width,args.expected_height],
    }
    try:
        assert re.fullmatch('[a-f0-9]{40}',args.source_sha)
        assert (args.expected_width,args.expected_height) in ((393,852),(360,800))
        assert args.actual.is_file() and args.reference.is_file()
        with Image.open(args.actual) as image:
            actual=image.convert('RGB')
        with Image.open(args.reference) as image:
            reference=image.convert('RGB')
        assert reference.size==(args.expected_width,args.expected_height), 'UX05BD_WRONG_REFERENCE_VIEWPORT'
        # Compose captures can exclude the Android status bar or navigation insets.
        # Require enough pixel density and a plausible portrait aspect ratio.
        assert actual.width>=args.expected_width*1.8
        assert actual.height>=args.expected_height*1.65
        assert actual.height>actual.width
        normalized=actual.resize(reference.size,Image.Resampling.LANCZOS)
        delta_image=ImageChops.difference(normalized,reference)
        mean=round(sum(ImageStat.Stat(delta_image).mean)/3,3)
        bands={}
        for name,top,bottom in [('top',0,.33),('middle',.33,.67),('bottom',.67,1)]:
            height=reference.height
            region=delta_image.crop((0,round(top*height),reference.width,round(bottom*height)))
            bands[name]=round(sum(ImageStat.Stat(region).mean)/3,3)
        normalized.save(out/'ux05bd-detail-native-normalized.png')
        delta_image.save(out/'ux05bd-detail-html-diff.png')
        receipt.update(actual_dimensions=list(actual.size),reference_dimensions=list(reference.size),
            mean_rgb_delta=mean,band_mean_rgb_deltas=bands,
            actual_sha256=hashlib.sha256(args.actual.read_bytes()).hexdigest(),
            approved_reference_sha256=hashlib.sha256(args.reference.read_bytes()).hexdigest())
        # Gross-drift guard only. No silent adoption or mutation of screenshot goldens.
        receipt['comparison_pass']=mean<=55.0
    except (OSError,ValueError,AssertionError) as err:
        receipt['error_category']=type(err).__name__
        receipt['error_code']=str(err)[:80] if isinstance(err,AssertionError) else type(err).__name__
    (out/'UX05BD_VISUAL_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if 'sha256' not in k},sort_keys=True))
    return 0 if receipt['comparison_pass'] else 1

if __name__=='__main__':raise SystemExit(run())
