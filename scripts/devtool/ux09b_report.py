#!/usr/bin/env python3
"""UX09B: compare authentic Compose captures with frozen HTML references.

Produces auditable candidate images and factual differences, NEVER silently
blesses a new native golden or marks full native parity as verified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

OFFLINE = ("home", "game-local", "saves-local", "mods-discover", "mods-installed",
           "mods-updates", "mods-profiles", "more")
SIZES = ((393, 852), (360, 800))
EXTRA_393 = ("saves-cloud-locked",)
COMPLETE_393 = ("home", "game-local", "game-steam-connected", "saves-local",
                "saves-cloud-locked", "saves-cloud-connected", "mods-discover",
                "mods-installed", "mods-updates", "mods-profiles", "more",
                "mod-detail", "operation-center", "download-queue",
                "file-access", "installation-health")
FULL_CASES = {f"{case}-{width}" for case in COMPLETE_393 for width in (393,)} | {
    f"{case}-360" for case in OFFLINE
}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_image(path: Path, size: tuple[int,int]):
    assert path.is_file() and not path.is_symlink(), 'UX09B_MISSING_IMAGE:'+str(path)
    with Image.open(path) as source:
        source.load()
        assert source.format == 'PNG' and source.size == size, 'UX09B_WRONG_PNG_SIZE:'+str(path)
        return source.convert('RGB')

def analyze(native_dir:Path,ref_dir:Path,layout_json:Path,out_dir:Path,
            source_sha:str,run_id:str,app_sha:str,test_sha:str)->dict:
    assert len(source_sha) == 40 and all(c in '0123456789abcdef' for c in source_sha), 'UX09B_UNPINNED_SOURCE'
    assert len(app_sha) == 64 and len(test_sha) == 64, 'UX09B_APK_PROVENANCE_MISSING'
    assert run_id.isdecimal(), 'UX09B_MISSING_RUN_ID'
    layout=json.loads(layout_json.read_text())
    assert len(layout) == 24, 'UX09B_REFERENCE_LAYOUT_COUNT_CHANGED'
    by_case={(x['screen'],x['viewport'][0]):x for x in layout}
    assert len(by_case)==24, 'UX09B_DUPLICATE_REFERENCE_CASE'
    expected={(case,width) for width,height in SIZES for case in OFFLINE} | {
        (case,393) for case in EXTRA_393
    }
    assert len(expected)==17, 'UX09B_CAPTURE_MATRIX_CHANGED'
    out_dir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for width,height in SIZES:
        for case in OFFLINE+(EXTRA_393 if width==393 else ()):
            key=f'{case}-{width}'
            native_file=native_dir/(key+'.png')
            reference_file=ref_dir/f'{case}-{width}x{height}.png'
            native=load_image(native_file,(width*2,height*2))
            reference=load_image(reference_file,(width,height))
            metadata_file=native_dir/(key+'.json')
            metadata=json.loads(metadata_file.read_text())
            assert metadata.get('case')==case and metadata.get('capture_px')==[width*2,height*2], 'UX09B_METADATA_DRIFT:'+key
            bounds=metadata.get('bounds')
            assert isinstance(bounds,list), 'UX09B_BOUNDS_MISSING:'+key
            tags={x['tag']:x['rect_px'] for x in bounds}
            assert 'cinderbox.shell.bottomnav' in tags, 'UX09B_NAV_SEMANTICS_MISSING:'+key
            assert 'cinderbox.shell.content' in tags, 'UX09B_CONTENT_SEMANTICS_MISSING:'+key
            approved=by_case[(case,width)]
            assert approved['viewport']==[width,height], 'UX09B_VIEWPORT_DRIFT'
            scaled=native.resize((width,height),Image.Resampling.LANCZOS)
            diff=ImageChops.difference(reference,scaled)
            # Cross-renderer differences are recorded, not passed using browser-only tolerances.
            from PIL import ImageStat
            mae=round(sum(ImageStat.Stat(diff).mean)/3,4)
            frac=round(sum(1 for v in diff.convert('L').getdata() if v>24)/(width*height),5)
            panel=Image.new('RGB',(width*3,height),(16,25,21))
            panel.paste(reference,(0,0));panel.paste(scaled,(width,0))
            panel.paste(diff.point(lambda x:min(255,x*3)),(width*2,0))
            d=ImageDraw.Draw(panel)
            d.rectangle((width,0,width*2-1,height-1),outline=(140,217,168),width=1)
            panel_file=out_dir/(key+'-compare.png')
            panel.save(panel_file,optimize=True)
            nav=tags['cinderbox.shell.bottomnav']
            # Rects are pixels at density 2. Compare only *documented* anchor delta.
            ref_bottom=approved['bottom']
            nav_top_dp=round(nav[1]/2,2)
            delta=round(nav_top_dp-ref_bottom[1],2)
            rows.append({
                'case':case,'viewport_css_px':[width,height],
                'native_capture_px':[width*2,height*2],
                'native_sha256':digest(native_file),'reference_sha256':digest(reference_file),
                'native_semantics_tags':sorted(tags),
                'native_nav_top_dp':nav_top_dp,
                'html_nav_top_px':ref_bottom[1],
                'nav_top_delta_px':delta,
                'mean_absolute_rgb_difference':mae,
                'diff_fraction_luma_gt_24':frac,
                'comparison_png':panel_file.name,
                'fixture_equivalence_verified':False,
                'approved_native_golden':False
            })
    captured={f"{r['case']}-{r['viewport_css_px'][0]}" for r in rows}
    assert captured.issubset(FULL_CASES) and len(captured)==17
    missing=sorted(FULL_CASES-captured)
    assert len(missing)==7
    receipt={
        'schema':'cinderbox-ux09b-evidence-v1',
        'result':'UX09B_NATIVE_CAPTURE_AND_DIFF_EVIDENCE_PASS',
        'source_sha':source_sha,'run_id':run_id,
        'app_sha256':app_sha,'instrumentation_apk_sha256':test_sha,
        'reference_cases':24,'native_cases_captured':len(rows),
        'missing_reference_cases':missing,
        'baseline_is_actual_activity_not_mocked_farm_or_account':True,
        'screenshot_metrics_are_diagnostic_not_visual_acceptance':True,
        'native_pixel_parity_verified':False,
        'native_goldens_approved':False,
        'full_24_case_parity_verified':False,
        'physical_device_qualified':False,
        'real_steam_entitlement_qualified':False,
        'live_mod_bulk_writes_enabled':False,
        'release_enabled':False,
        'cases':rows
    }
    (out_dir/'UX09B_EVIDENCE.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    (out_dir/'UX09B_REVIEW.md').write_text(
        '# UX-09B native screenshot candidate review\n\n'
        f'Source: `{source_sha}`; hosted run `{run_id}`. '\
        f'Captured **{len(rows)} of 24** approved browser states in Compose.\n\n'
        '**NOT APPROVED:** live empty local data differs from HTML demo fixtures, and system bars, '\
        'font rendering, and density must be qualified before native goldens can be committed.\n\n'
        'Metrics are informational and cannot turn candidate screenshots into pixel-parity acceptance.\n\n'
        '| Screen | Width | Mean RGB delta | Pixel fraction (luma > 24) | Nav-top delta |\n'
        '|---|---:|---:|---:|---:|\n'+
        ''.join(f"| {r['case']} | {r['viewport_css_px'][0]} | {r['mean_absolute_rgb_difference']} | "
                f"{r['diff_fraction_luma_gt_24']:.2%} | {r['nav_top_delta_px']}px |\n" for r in rows)+
        '\nNot captured / NOT qualified: '+', '.join(missing)+'\n'
    )
    return receipt

def main():
    p=argparse.ArgumentParser()
    for name in ('native-dir','reference-dir','layout-json','out-dir','source-sha','run-id','app-sha','test-sha'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    r=analyze(Path(a.native_dir),Path(a.reference_dir),Path(a.layout_json),
        Path(a.out_dir),a.source_sha,a.run_id,a.app_sha,a.test_sha)
    print(r['result'],r['native_cases_captured'],'of',r['reference_cases'],
        'native screenshots; full parity remains unqualified')

if __name__=='__main__':main()
