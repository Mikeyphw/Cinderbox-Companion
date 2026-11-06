#!/usr/bin/env python3
"""Extend UX09B's 17 actual native screenshots with four real deep routes.

There are no fabricated connected Steam states, unsafe file operations, or
implicitly approved native goldens. Cross-renderer pixel differences are
observations only and the HTML reference remains immutable.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat

DEEP = ('download-queue','file-access','operation-center','installation-health')
REMAINING = ('game-steam-connected-393','mod-detail-393','saves-cloud-connected-393')

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def analyze(evidence_dir:Path,reference_dir:Path,source_sha:str,run_id:str,app_sha:str,test_sha:str)->dict:
    assert len(source_sha)==40 and all(c in '0123456789abcdef' for c in source_sha), 'UX09B2_INVALID_SHA'
    assert len(app_sha)==64 and len(test_sha)==64 and run_id.isdecimal(), 'UX09B2_INVALID_PROVENANCE'
    base=json.loads((evidence_dir/'UX09B_EVIDENCE.json').read_text())
    assert base['source_sha']==source_sha and base['run_id']==run_id, 'UX09B2_BASE_SOURCE_MISMATCH'
    assert base['app_sha256']==app_sha and base['instrumentation_apk_sha256']==test_sha, 'UX09B2_APK_MISMATCH'
    assert base['native_cases_captured']==17 and len(base['cases'])==17, 'UX09B2_BASE_CASES_INCOMPLETE'
    assert base['native_goldens_approved'] is False and base['full_24_case_parity_verified'] is False
    existing={f"{r['case']}-{r['viewport_css_px'][0]}" for r in base['cases']}
    assert len(existing)==17 and not any(f'{c}-393' in existing for c in DEEP)
    for row in base['cases']:
        k=f"{row['case']}-{row['viewport_css_px'][0]}"
        assert digest(evidence_dir/(k+'.png'))==row['native_sha256'], 'UX09B2_17_BASE_DIGEST_CHANGED:'+k
    extensions=[]
    for c in DEEP:
        key=f'{c}-393';np=evidence_dir/(key+'.png');rp=reference_dir/(key+'x852.png')
        assert np.is_file() and rp.is_file() and not np.is_symlink() and not rp.is_symlink()
        meta=json.loads((evidence_dir/(key+'.json')).read_text())
        assert meta['case']==c and meta['capture_px']==[786,1704], 'UX09B2_BAD_NATIVE_METADATA:'+key
        assert meta['actual_activity'] is True and meta['offline'] is True and meta['route_asserted'] is True
        assert meta['credential_or_entitlement_fixture'] is False
        with Image.open(np) as n,Image.open(rp) as r:
            n.load();r.load()
            assert n.format=='PNG' and n.size==(786,1704), 'UX09B2_NATIVE_SIZE_MISMATCH:'+key
            assert r.format=='PNG' and r.size==(393,852), 'UX09B2_REFERENCE_SIZE_MISMATCH:'+key
            native=n.convert('RGB').resize((393,852),Image.Resampling.LANCZOS)
            reference=r.convert('RGB')
        difference=ImageChops.difference(reference,native)
        mae=round(sum(ImageStat.Stat(difference).mean)/3,4)
        fraction=round(sum(v>24 for v in difference.convert('L').getdata())/(393*852),5)
        triptych=Image.new('RGB',(1179,852),(16,25,21))
        triptych.paste(reference,(0,0));triptych.paste(native,(393,0))
        triptych.paste(difference.point(lambda value:min(255,value*3)),(786,0))
        drawer=ImageDraw.Draw(triptych);drawer.line([(393,0),(393,851)],fill=(140,217,168))
        name=key+'-compare.png';triptych.save(evidence_dir/name,optimize=True)
        extensions.append({'case':c,'viewport_css_px':[393,852],'native_capture_px':[786,1704],
          'native_sha256':digest(np),'reference_sha256':digest(rp),'comparison_png':name,
          'mean_absolute_rgb_difference':mae,'diff_fraction_luma_gt_24':fraction,
          'native_origin':'offline-hosted-real-activity','fixture_equivalence_verified':False,
          'approved_native_golden':False})
    observed=existing|{f'{c}-393' for c in DEEP}
    assert len(observed)==21
    assert base['reference_cases']==24
    missing=sorted(set(base['missing_reference_cases'])-{f'{c}-393' for c in DEEP})
    assert missing==sorted(REMAINING), 'UX09B2_UNEXPECTED_GAP:'+repr(missing)
    result={
      'schema':'cinderbox-ux09b2-evidence-v1','result':'UX09B2_REAL_DEEP_CAPTURE_EVIDENCE_PASS',
      'source_sha':source_sha,'run_id':run_id,'app_sha256':app_sha,'test_apk_sha256':test_sha,
      'browser_reference_cases':24,'actual_native_cases':21,'new_real_deep_routes':4,
      'missing_reference_cases':missing,
      'read_only_synthetic_emulator':True,'production_credentials_faked':False,
      'real_steam_auth_and_entitlement_qualified':False,
      'native_pixel_parity_verified':False,'native_goldens_approved':False,
      'all_24_states_covered':False,'physical_device_qualified':False,
      'live_mod_bulk_writes_enabled':False,'release_enabled':False,'publication_enabled':False,
      'original_17_case_receipt':'UX09B_EVIDENCE.json','additional_cases':extensions
    }
    (evidence_dir/'UX09B2_EVIDENCE.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (evidence_dir/'UX09B2_REVIEW.md').write_text(
      '# UX09B2: four additional real Android deep-screen captures\n\n'
      f'Exact source: `{source_sha}`; CI run `{run_id}`.\n\n'
      '21/24 approved browser cases now have native Android counterparts; **not pixel-parity approved**.\n'
      'No injected farms, mods, sessions, credentials or provider permissions.\n\n'
      '| Deep route | Mean RGB difference | Fraction >24 luma |\n|---|---:|---:|\n'+
      ''.join(f"| {r['case']} | {r['mean_absolute_rgb_difference']} | {r['diff_fraction_luma_gt_24']:.2%} |\n" for r in extensions)+
      '\nStill missing: '+', '.join(missing)+
      '\n\nThe frozen HTML has synthetic data and geometry; native actual offline state differs. '
      'Screenshots and diff images are evidence only, and no golden or device acceptance is inferred.\n')
    return result

def main():
    a=argparse.ArgumentParser()
    for arg in ('evidence-dir','reference-dir','source-sha','run-id','app-sha','test-sha'):
        a.add_argument('--'+arg,required=True)
    v=vars(a.parse_args())
    receipt=analyze(Path(v['evidence_dir']),Path(v['reference_dir']),
      v['source_sha'],v['run_id'],v['app_sha'],v['test_sha'])
    print(receipt['result'],receipt['actual_native_cases'],'of',receipt['browser_reference_cases'],
          'with',len(receipt['missing_reference_cases']),'explicitly unqualified states')

if __name__=='__main__':main()
