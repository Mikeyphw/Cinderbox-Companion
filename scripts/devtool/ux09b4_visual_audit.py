#!/usr/bin/env python3
"""UX-09B4 native geometry / status inset audit — evidence ONLY, no golden blessing.

21 genuine offline MainActivity states and 3 isolated, UI-only preview states.
Do not normalize away physical Android system bars or infer account/file access.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, statistics
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

FIXTURES = ("game-steam-connected", "saves-cloud-connected", "mod-detail")
DEEP = ("download-queue", "file-access", "operation-center", "installation-health")
EXPECTED_COUNT=24

def digest(p:Path) -> str:
    assert p.is_file() and not p.is_symlink(), 'UX09B4_MISSING_OR_SYMLINK:'+str(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_png(p:Path,size:tuple[int,int]) -> Image.Image:
    assert p.is_file() and not p.is_symlink(), 'UX09B4_MISSING_IMAGE:'+str(p)
    with Image.open(p) as im:
        im.load()
        assert im.format == 'PNG' and im.size == size, 'UX09B4_WRONG_IMAGE_SIZE:'+str(p)
        return im.convert('RGB')

def mae(left:Image.Image,right:Image.Image) -> float:
    assert left.size == right.size
    d=ImageChops.difference(left,right)
    return round(sum(ImageStat.Stat(d).mean)/3,4)

def independent_colors(img:Image.Image) -> int:
    # Cover actual text and cards above/below the old narrow center band.
    # A frame still fails if it lacks visible foreground or diverse pixels.
    w,h=img.size; colors=set(); foreground=0
    for y in range(h//8,(h*7)//8,13):
        for x in range(w//12,(w*11)//12,13):
            r,g,b=img.getpixel((x,y))
            colors.add((r,g,b))
            if max(r,g,b)>115 and min(r,g,b)>70:
                foreground+=1
    assert foreground>=8, 'UX09B4_NO_VISIBLE_FOREGROUND'
    return len(colors)

def analyze(evidence:Path,reference:Path,layout_path:Path,sha:str,run_id:str)->dict:
    assert len(sha)==40 and all(v in '0123456789abcdef' for v in sha), 'UX09B4_INVALID_SHA'
    assert run_id.isdecimal(), 'UX09B4_INVALID_RUN_ID'
    a=json.loads((evidence/'UX09B_EVIDENCE.json').read_text())
    b=json.loads((evidence/'UX09B2_EVIDENCE.json').read_text())
    c=json.loads((evidence/'UX09B3_EVIDENCE.json').read_text())
    for receipt in (a,b,c):
        assert receipt['source_sha']==sha and str(receipt['run_id'])==run_id, 'UX09B4_SOURCE_RUN_MISMATCH'
        assert receipt.get('native_goldens_approved') is False, 'UX09B4_PREAPPROVED_GOLDEN_REFUSED'
        assert receipt.get('native_pixel_parity_verified') is False, 'UX09B4_PREAPPROVED_PARITY_REFUSED'
    assert a['native_cases_captured']==17 and b['actual_native_cases']==21, 'UX09B4_ACTUAL_CASE_COUNT'
    assert c['actual_real_activity_cases']==21 and c['isolated_preview_fixture_cases']==3, 'UX09B4_ORIGIN_MIXUP'
    assert c['native_candidate_cases']==EXPECTED_COUNT and c['full_24_case_parity_verified'] is False
    assert c['production_credentials_faked'] is False and c['real_steam_auth_and_entitlement_qualified'] is False
    assert c['release_enabled'] is False and c['live_mod_bulk_writes_enabled'] is False
    layout=json.loads(layout_path.read_text())
    assert isinstance(layout,list) and len(layout)==EXPECTED_COUNT, 'UX09B4_REFERENCE_MATRIX_DRIFT'
    mapping={(x['screen'],x['viewport'][0]):x for x in layout}
    assert len(mapping)==EXPECTED_COUNT, 'UX09B4_DUPLICATE_REFERENCE'
    real={(x['case'],x['viewport_css_px'][0]):x for x in a['cases']}
    assert len(real)==17
    deep={(x['case'],x['viewport_css_px'][0]):x for x in b['additional_cases']}
    assert set(deep)=={(name,393) for name in DEEP}, 'UX09B4_DEEP_COUNT_DRIFT'
    fixtures={(x['case'],x['viewport_css_px'][0]):x for x in c['fixture_cases']}
    assert set(fixtures)=={(name,393) for name in FIXTURES}, 'UX09B4_FIXTURE_COUNT_DRIFT'
    combined={**real,**deep,**fixtures}
    assert len(combined)==EXPECTED_COUNT and set(combined)==set(mapping), 'UX09B4_MATRIX_INCOMPLETE'
    nav_deltas=[];rows=[]
    for case,width in sorted(combined):
        row=combined[(case,width)];ref=mapping[(case,width)];height=ref['viewport'][1]
        assert ref['viewport']==[width,height], 'UX09B4_VIEWPORT_MISMATCH'
        key=f'{case}-{width}'
        native_file=evidence/(key+'.png');browser_file=reference/(key+f'x{height}.png')
        assert row['native_sha256']==digest(native_file), 'UX09B4_NATIVE_DIGEST_CHANGED:'+key
        assert row['reference_sha256']==digest(browser_file), 'UX09B4_BROWSER_DIGEST_CHANGED:'+key
        native=load_png(native_file,(width*2,height*2)).resize((width,height),Image.Resampling.LANCZOS)
        browser=load_png(browser_file,(width,height))
        assert independent_colors(native)>=10, 'UX09B4_EMPTY_IMAGE:'+key
        status_h=round(ref['status'][3]);nav_start=round(ref['bottom'][1]);
        assert 18<=status_h<=40 and nav_start>status_h+100 and nav_start<=height, 'UX09B4_BAD_REFERENCE_RECTS'
        total=mae(native,browser)
        content=mae(native.crop((0,status_h,width,nav_start)),browser.crop((0,status_h,width,nav_start)))
        origin='real-offline-mainactivity' if (case,width) in real or (case,width) in deep else 'isolated-composable-preview'
        note=[]
        if (case,width) in real:
            delta=row['nav_top_delta_px'];nav_deltas.append(delta)
            if abs(delta)>2: note.append('bottom-nav-geometry-review')
        if (case,width) in fixtures:
            md=json.loads((evidence/(key+'.json')).read_text())
            assert md['case']==case and md['isolated_compose_fixture'] is True
            assert md['actual_main_activity_route'] is False
            assert md['real_steam_authentication'] is False and md['real_steam_entitlement'] is False
            assert md['real_cloud_access'] is False and md['production_state_mutated'] is False
            assert md.get('status_bar_safe_area_asserted') is True, 'UX09B4_NO_SAFE_AREA_ASSERTION:'+key
            assert md.get('safe_area_kind')=='isolated-fixture-compose-statusBars', 'UX09B4_WRONG_INSET_KIND:'+key
            top=md.get('content_top_px')
            assert isinstance(top,(float,int)) and 40<=top<=120, 'UX09B4_STATUS_BAR_OVERLAP:'+key
            if case=='mod-detail':
                assert md.get('display_content_nonblank') is True and md.get('display_sampled_unique_colors',0)>=12
            note.append('example-fixture-not-genuine-account-or-catalog')
        rows.append({'case':case,'width_css_px':width,'height_css_px':height,'origin':origin,
          'native_sha256':digest(native_file),'reference_sha256':digest(browser_file),
          'full_frame_mae_rgb':total,'content_band_mae_rgb':content,
          'status_reference_px':status_h,'reference_nav_y_px':nav_start,
          'native_nav_delta_px':row.get('nav_top_delta_px'),
          'visual_equivalence_approved':False,'review_flags':note})
    assert len(nav_deltas)==17,'UX09B4_NAV_OBSERVATIONS_MISSING'
    receipt={
      'schema':'cinderbox-ux09b4-visual-geometry-v1','result':'UX09B4_SAFE_AREA_AND_GEOMETRY_EVIDENCE_PASS',
      'source_sha':sha,'run_id':run_id,'approved_browser_reference_cases':24,
      'real_mainactivity_cases':21,'isolated_presentation_fixture_cases':3,'cases':rows,
      'native_nav_offset_range_dp':[min(nav_deltas),max(nav_deltas)],
      'native_nav_offset_median_dp':statistics.median(nav_deltas),
      'browser_native_data_fixture_equivalent':False,
      'native_goldens_approved':False,'native_pixel_parity_verified':False,
      'real_steam_auth_and_entitlement_qualified':False,'physical_device_qualified':False,
      'release_enabled':False,'publication_enabled':False,'live_mod_bulk_writes_enabled':False,
      'system_bars_excluded_from_content_band_metric_but_not_native_screenshots':True,
      'content_band_metrics_diagnostic_only':True
    }
    (evidence/'UX09B4_VISUAL_AUDIT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    with (evidence/'UX09B4_CASE_MATRIX.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['case','width_css_px','height_css_px','origin',
            'full_frame_mae_rgb','content_band_mae_rgb','native_nav_delta_px',
            'visual_equivalence_approved'])
        writer.writeheader()
        for r in rows:writer.writerow({k:r[k] for k in writer.fieldnames})
    notes='\n'.join(f"| {r['case']} | {r['width_css_px']} | {r['origin']} | {r['full_frame_mae_rgb']} | {r['content_band_mae_rgb']} |"
                    for r in rows)
    (evidence/'UX09B4_VISUAL_REVIEW.md').write_text(
      '# UX-09B4: 24-case audited native screenshot candidates\n\n'
      f'Exact source `{sha}`, hosted run `{run_id}`. **No native goldens approved.**\n\n'
      'A 24-case screenshot matrix is not proof of 24 visual matches: 21 real offline routes, '
      '3 in-memory Compose previews. The original dark HTML contains synthetic farm/mod data.\n\n'
      'The test-only Compose fixtures now assert their content is below the Android status bar. '
      'Actual native screens are not modified. System bars remain in all original captured PNGs.\n\n'
      'The content-band metric excludes only the top browser status rectangle and bottom browser '
      'nav rectangle. It **does not** normalize away actual system insets or imply approved parity.\n\n'
      f'Actual primary route bottom navigation offset: {receipt["native_nav_offset_range_dp"]} dp; '
      'do not remove Android navigation safety padding just to chase reference coordinates.\n\n'
      '| Case | Width | Source | Full RGB MAE | Content-band RGB MAE |\n|---|---:|---|---:|---:|\n'+notes+'\n\n'
      '**Pending manual comparison:** actual content fixtures, mod artwork/assets, precise safe-area '
      'treatment, responsive spacing/typography and independently approved native-only goldens.\n')
    return receipt

def main():
    p=argparse.ArgumentParser()
    for arg in ('evidence-dir','reference-dir','layout-json','source-sha','run-id'):p.add_argument('--'+arg,required=True)
    a=p.parse_args();r=analyze(Path(a.evidence_dir),Path(a.reference_dir),Path(a.layout_json),a.source_sha,a.run_id)
    print(r['result'],len(r['cases']),'cases; median native nav offset',r['native_nav_offset_median_dp'],
      'dp; no native goldens approved')
if __name__=='__main__': main()
