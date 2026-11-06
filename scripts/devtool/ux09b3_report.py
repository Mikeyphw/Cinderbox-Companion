#!/usr/bin/env python3
"""Coverage of the three reference-only states via isolated Compose fixtures.

This explicitly does NOT grant parity, authenticate Steam, approve native goldens,
or reclassify fixture UI as a real user state. 21 real routes + 3 previews.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat

FIXTURE_CASES = ('game-steam-connected','saves-cloud-connected','mod-detail')
REFERENCE_CASES = 24

def sha256(p:Path)->str:
    assert p.is_file() and not p.is_symlink(), 'UX09B3_MISSING_OR_SYMLINK:'+str(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def visible_native_frame(image:Image.Image,case:str)->int:
    """Refuse a uniform UI body even when the file is a valid PNG with a hash.

    The crop excludes Android status/navigation bars. Deliberately conservative:
    this is a nonblank guard, NOT a visual fidelity threshold.
    """
    rgb=image.convert('RGB')
    w,h=rgb.size
    interior=rgb.crop((w//8,h//4,w*7//8,h*3//4))
    sample=interior.resize((64,64),Image.Resampling.NEAREST)
    diversity=len(sample.getcolors(64*64) or [])
    assert diversity>=12, 'UX09B3_BLANK_NATIVE_FRAME:'+case
    return diversity

def analyze(evidence_dir:Path,reference_dir:Path,layout_json:Path,source_sha:str,run_id:str,app_sha:str,test_sha:str)->dict:
    assert len(source_sha)==40 and all(x in '0123456789abcdef' for x in source_sha), 'UX09B3_BAD_SOURCE'
    assert len(app_sha)==64 and len(test_sha)==64 and run_id.isdecimal(), 'UX09B3_BAD_PROVENANCE'
    base=json.loads((evidence_dir/'UX09B_EVIDENCE.json').read_text())
    deep=json.loads((evidence_dir/'UX09B2_EVIDENCE.json').read_text())
    for receipt in (base,deep):
        assert receipt['source_sha']==source_sha and receipt['run_id']==run_id, 'UX09B3_DIFFERENT_SOURCE'
        assert receipt['app_sha256']==app_sha, 'UX09B3_DIFFERENT_APK'
    assert base['instrumentation_apk_sha256']==test_sha and deep['test_apk_sha256']==test_sha, 'UX09B3_DIFFERENT_TEST_APK'
    assert base['native_cases_captured']==17 and deep['actual_native_cases']==21
    assert base['native_goldens_approved'] is False and deep['native_goldens_approved'] is False
    assert deep['missing_reference_cases']==sorted(c+'-393' for c in FIXTURE_CASES), 'UX09B3_UNEXPECTED_GAP'
    for entry in base['cases']:
        name=f"{entry['case']}-{entry['viewport_css_px'][0]}.png"
        assert sha256(evidence_dir/name)==entry['native_sha256'], 'UX09B3_REAL_CAPTURE_CHANGED:'+name
    for entry in deep['additional_cases']:
        name=f"{entry['case']}-393.png"
        assert sha256(evidence_dir/name)==entry['native_sha256'], 'UX09B3_DEEP_CAPTURE_CHANGED:'+name
    layout=json.loads(layout_json.read_text())
    assert len(layout)==REFERENCE_CASES, 'UX09B3_REFERENCE_COUNT_DRIFT'
    approved={(r['screen'],r['viewport'][0]):r for r in layout}
    assert len(approved)==REFERENCE_CASES, 'UX09B3_DUPLICATE_BROWSER_REFERENCE'
    entries=[]
    for case in FIXTURE_CASES:
        key=case+'-393'
        native_file=evidence_dir/(key+'.png')
        reference_file=reference_dir/(key+'x852.png')
        meta=json.loads((evidence_dir/(key+'.json')).read_text())
        assert meta['case']==case and meta['capture_px']==[786,1704], 'UX09B3_BAD_FIXTURE_META:'+case
        for field,truth in {
            'isolated_compose_fixture':True,'actual_main_activity_route':False,
            'steam_ui_boolean_preview':case!='mod-detail','real_steam_authentication':False,
            'real_steam_entitlement':False,'real_cloud_access':False,
            'provider_catalog_verified':False,'production_state_mutated':False,
            'display_content_nonblank':True,
        }.items():
            assert meta.get(field) is truth, 'UX09B3_INVALID_FIXTURE_CLAIM:'+field
        assert meta.get('capture_method')=='android-ui-automation-full-display', 'UX09B3_UNVERIFIED_CAPTURE_METHOD:'+case
        assert isinstance(meta.get('display_sampled_unique_colors'),int) and meta['display_sampled_unique_colors']>=12, 'UX09B3_NOT_RENDERED:'+case
        assert isinstance(meta.get('display_capture_attempt'),int) and 1<=meta['display_capture_attempt']<=12, 'UX09B3_UNBOUNDED_RETRY:'+case
        assert approved[(case,393)]['viewport']==[393,852]
        with Image.open(native_file) as n, Image.open(reference_file) as r:
            n.load();r.load()
            assert n.format=='PNG' and n.size==(786,1704), 'UX09B3_WRONG_NATIVE_PNG:'+case
            assert r.format=='PNG' and r.size==(393,852), 'UX09B3_WRONG_REFERENCE_PNG:'+case
            independentDiversity=visible_native_frame(n,case)
            native=n.convert('RGB').resize((393,852),Image.Resampling.LANCZOS)
            reference=r.convert('RGB')
        difference=ImageChops.difference(reference,native)
        average=round(sum(ImageStat.Stat(difference).mean)/3,4)
        fraction=round(sum(px>24 for px in difference.convert('L').getdata())/(393*852),5)
        strip=Image.new('RGB',(1179,852),(16,25,21))
        strip.paste(reference,(0,0));strip.paste(native,(393,0))
        strip.paste(difference.point(lambda v:min(255,v*3)),(786,0))
        ImageDraw.Draw(strip).line([(393,0),(393,851)],fill=(140,217,168))
        comparison=key+'-compare.png'
        strip.save(evidence_dir/comparison,optimize=True)
        entries.append({
            'case':case,'viewport_css_px':[393,852],'native_capture_px':[786,1704],
            'native_sha256':sha256(native_file),'reference_sha256':sha256(reference_file),
            'comparison_png':comparison,'mean_absolute_rgb_difference':average,
            'diff_fraction_luma_gt_24':fraction,
            'origin':'isolated-compose-presentation-fixture','actual_user_data':False,
            'real_authentication_verified':False,'fixture_equivalence_verified':False,
            'approved_native_golden':False,
            'nonblank_frame_verified':True,'independent_sampled_colors':independentDiversity,
            'display_capture_attempt':meta['display_capture_attempt'],
        })
    receipt={
        'schema':'cinderbox-ux09b3-presentation-fixture-evidence-v1',
        'result':'UX09B3_24_SCREENSHOT_CANDIDATES_UNAPPROVED',
        'source_sha':source_sha,'run_id':run_id,
        'app_sha256':app_sha,'test_apk_sha256':test_sha,
        'browser_reference_cases':24,'native_candidate_cases':24,
        'actual_real_activity_cases':21,'isolated_preview_fixture_cases':3,
        'missing_screenshot_cases':[],
        'comparison_is_diagnostic_only':True,
        'all_24_states_covered_as_screenshot_candidates':True,
        'full_24_case_parity_verified':False,
        'fixture_equivalence_verified':False,
        'native_goldens_approved':False,'native_pixel_parity_verified':False,
        'production_credentials_faked':False,'real_steam_auth_and_entitlement_qualified':False,
        'real_steam_cloud_qualified':False,'real_mod_catalog_qualified':False,
        'physical_device_qualified':False,'live_mod_bulk_writes_enabled':False,
        'release_enabled':False,'publication_enabled':False,
        'observed_receipts':['UX09B_EVIDENCE.json','UX09B2_EVIDENCE.json'],
        'fixture_cases':entries
    }
    (evidence_dir/'UX09B3_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    lines=[
        '# UX09B3 — screenshot coverage, NOT screenshot parity',
        '',f'Source `{source_sha}` | hosted run `{run_id}`', '',
        '**21 actual MainActivity screenshot candidates, plus three isolated presentation-only fixtures.**',
        'The 24 browser cases are covered by captures; not one native golden is implicitly approved.',
        'Connected Steam UI booleans DO NOT represent credentials, authentication, entitlement or cloud access.',
        'The mod example is in-memory metadata, not a provider catalog response or installation.',
        'The real local-first Android dataset still differs from the frozen browser demo.', '',
        '| Isolated preview | Mean RGB difference | Pixel fraction >24 luma |',
        '|---|---:|---:|'
    ]
    lines += [f"| {r['case']} | {r['mean_absolute_rgb_difference']} | {r['diff_fraction_luma_gt_24']:.2%} |" for r in entries]
    lines += ['', '**Remaining qualification:** match deterministic UI data across renderers, measure insets and type/layout bounds, independently review native screenshots before pinning native-only goldens, test 200% font scaling/IME/lifecycle in UX09C, and perform real auth and device acceptance separately.']
    (evidence_dir/'UX09B3_REVIEW.md').write_text('\n'.join(lines)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser()
    for arg in ('evidence-dir','reference-dir','layout-json','source-sha','run-id','app-sha','test-sha'):
        p.add_argument('--'+arg,required=True)
    a=vars(p.parse_args())
    receipt=analyze(Path(a['evidence_dir']),Path(a['reference_dir']),Path(a['layout_json']),
        a['source_sha'],a['run_id'],a['app_sha'],a['test_sha'])
    print(receipt['result'],receipt['actual_real_activity_cases'],receipt['isolated_preview_fixture_cases'])

if __name__=='__main__':main()
