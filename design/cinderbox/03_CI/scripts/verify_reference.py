#!/usr/bin/env python3
"""Portable, real-browser UI golden/geometry/interaction check for the approved Cinderbox HTML.

Dependencies (CI only): playwright==1.57.0, Pillow>=11.0; Chromium. No Android build here.
Uses page.set_content() so file:// permissions cannot cause a blank mockup.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / '01_REFERENCE' / 'cinderbox-portrait-DARK.html'
CONTRACT = ROOT / '02_CONTRACT' / 'ux-contract.json'
SCREENSHOTS = ROOT / '01_REFERENCE' / 'screenshots'
SCREENS = [
 ('home','nav("home")','Your valley'),
 ('game-local','nav("game")','Connect Steam to download'),
 ('saves-local','nav("saves")','Local saves are always available'),
 ('mods-discover','nav("mods");state.modsPane="discover";render(true)','Explore'),
 ('mods-installed','nav("mods");state.modsPane="installed";render(true)','Installed'),
 ('mods-updates','nav("mods");state.modsPane="updates";render(true)','Updates'),
 ('mods-profiles','nav("mods");state.modsPane="profiles";render(true)','Profiles'),
 ('more','nav("more")','Steam'),
 ('saves-cloud-locked','nav("saves");state.savedPane="cloud";render(true)','Cloud saves are optional'),
 ('game-steam-connected','action("steam-demo-connect");nav("game")','Choose download branch'),
 ('saves-cloud-connected','action("steam-demo-connect");nav("saves");state.savedPane="cloud";render(true)','No cloud saves loaded'),
 ('mod-detail','nav("mods");state.activeMod="1";state.screen="moddetail";render(true)','Expanded Valley'),
 ('installation-health','state.screen="health";render(true)','Installation'),
 ('operation-center','state.screen="activity";render(true)','Activity'),
 ('file-access','state.screen="file-access";render(true)','File access'),
 ('download-queue','state.screen="queue";render(true)','Download'),
]

def launch_browser(p):
    # Use normal Playwright-pinned chromium in GitHub, local system chrome for baseline generation.
    browser_path=os.environ.get('CINDERBOX_CHROMIUM')
    kw={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
    if browser_path: kw['executable_path']=browser_path
    return p.chromium.launch(**kw)

def measure(page):
    return page.evaluate('''() => {const rect=(s)=>{let e=document.querySelector(s); if(!e)return null;let r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height].map(v=>Math.round(v*10)/10)};
      const st=getComputedStyle(document.documentElement);
      return {device:rect('.device'),status:rect('.status'),header:rect('.shell-head'),content:rect('.content'),bottom:rect('.bottom'),
      anchors:{pageHeader:rect('.page-head'),hero:rect('.hero'),firstCard:rect('.card'),firstStat:rect('.stat'),sectionHeading:rect('.section-title'),segment:rect('.seg'),search:rect('.search'),firstChip:rect('.chip'),modGrid:rect('.modgrid'),firstMod:rect('.modcard'),firstSave:rect('.save-card'),firstSetting:rect('.settings-item'),firstButton:rect('.btn'),firstSheet:rect('.sheet')},
      nav:document.querySelectorAll('.bottom button').length, bg:st.getPropertyValue('--bg').trim(), paper:st.getPropertyValue('--paper').trim(),
      ink:st.getPropertyValue('--ink').trim(), theme:document.documentElement.dataset.theme,
      contentLength:document.querySelector('#content')?.innerText.length??0,
      documentWidth: document.documentElement.scrollWidth};}''')

def verify_screen_image(actual: Path, golden: Path):
    if not golden.exists(): raise AssertionError('Golden PNG absent: '+str(golden))
    im=Image.open(actual).convert('RGB'); gi=Image.open(golden).convert('RGB')
    if im.size!=gi.size: raise AssertionError(f'Image dimension drift {actual.name}: {im.size} vs {gi.size}')
    diff=ImageChops.difference(im,gi)
    means=ImageStat.Stat(diff).mean
    # Generous pixel tolerance for font anti-aliasing variations; geometry is separately strict.
    avg=sum(means)/3
    if avg>7.0: raise AssertionError(f'Screenshot {actual.name} differs significantly: mean RGB channel delta {avg:.2f} > 7.0')
    return round(avg,3)

def run(update):
    c=json.loads(CONTRACT.read_text())
    data=REFERENCE.read_bytes();sha=hashlib.sha256(data).hexdigest()
    if not update: assert sha==c['reference']['sha256'],f'REFERENCE_IMMUTABILITY_FAIL expected {c["reference"]["sha256"]} got {sha}'
    source=data.decode('utf8')
    assert '<html lang="en" data-theme="dark">' in source
    assert source.count('<section class="offline-screen"')>=5, 'No static fallback'
    assert 'function renderTopBar()' in source and 'function top()' not in source
    assert 'steam:false' in source and "theme:'dark'" in source
    assert 'theme:light' not in source and 'theme:dark' not in source, 'Alternate theme controls returned'
    assert 'Dark · default' in source, 'Single-dark appearance missing' 
    assert 'game_idle_lock_qualified' not in source or 'true' not in source
    SCREENSHOTS.mkdir(exist_ok=True, parents=True)
    geometry=[];results=[]
    with sync_playwright() as p:
      browser=launch_browser(p)
      for viewport in ((393,852),(360,800)):
        cases=SCREENS if viewport[0]==393 else SCREENS[:8]
        for name,cmd,expected in cases:
            page=browser.new_page(viewport={'width':viewport[0],'height':viewport[1]},device_scale_factor=1,reduced_motion='reduce')
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content(source,wait_until='load')
            assert not errors,f'Browser parse error before test {name}: {errors}'
            assert page.locator('.bottom button').count()==5,f'{name} blank nav'
            page.evaluate(cmd)
            assert not errors,f'Browser runtime error {name}: {errors}'
            text=page.locator('#content').inner_text()
            assert expected.lower() in text.lower(),f'{name}: missing expected content {expected!r}'
            assert len(text)>100,f'{name}: blank content'
            m=measure(page)
            assert m['theme']=='dark',f'Dark mode changed unexpectedly: {name}'
            assert m['bg']=='#101915' and m['paper']=='#1b2922',f'Token mismatch {name}: {m}'
            assert m['nav']==5
            assert m['documentWidth']<=viewport[0]+1,f'Horizontal overflow {name} at {viewport}: {m["documentWidth"]}'
            if update:
                gold=SCREENSHOTS / f'{name}-{viewport[0]}x{viewport[1]}.png'
                page.screenshot(path=str(gold),animations='disabled')
            else:
                from tempfile import TemporaryDirectory
                with TemporaryDirectory() as td:
                    actual=Path(td)/f'{name}-{viewport[0]}x{viewport[1]}.png'
                    page.screenshot(path=str(actual),animations='disabled')
                    d=verify_screen_image(actual,SCREENSHOTS/actual.name)
                    results.append((name,viewport,d))
            geometry.append({'screen':name,'viewport':list(viewport),**m})
            page.close()
      # Browser with JavaScript disabled must still show Home + 5 fallback navigation links
      page=browser.new_page(viewport={'width':393,'height':852},java_script_enabled=False)
      page.set_content(source,wait_until='load')
      assert page.locator('#offline-home').is_visible(), 'No-JS home blank'
      assert page.locator('.bottom a.navitem').count()==5, 'No-JS nav absent'
      page.locator('.bottom a[href="#offline-mods"]').click()
      assert page.locator('#offline-mods').is_visible(), 'No-JS Mods navigation failed'
      page.close()
      # The baseline starts disconnected; local features are usable without Steam.
      page=browser.new_page(viewport={'width':393,'height':852})
      page.set_content(source,wait_until='load')
      assert page.evaluate('state.steam') is False
      page.evaluate('nav("game")');assert 'Connect Steam to download' in page.locator('#content').inner_text()
      page.evaluate('nav("saves");state.savedPane="cloud";render(true)')
      assert 'Cloud saves are optional' in page.locator('#content').inner_text()
      page.evaluate('action("steam-demo-connect")')
      assert page.evaluate('state.steam') is True
      page.evaluate('action("steam-disconnect")')
      assert page.evaluate('state.steam') is False
      page.evaluate('nav("mods");state.modsPane="discover";render(true)')
      assert 'Explore' in page.locator('#content').inner_text()
      # All 15 approved secondary routes must genuinely render without throwing in Chromium.
      deeper=['moddetail','savedetail','backups','health','activity','smapi','recovery','game-download',
              'file-access','diagnostics','help','about','queue','profile','installed-detail']
      detail_errors=[];page.on('pageerror',lambda e:detail_errors.append(str(e)))
      for route in deeper:
          page.evaluate('''r => {state.activeMod='1';state.activeSave='Willowbrook';state.screen=r;render(true)}''', route)
          assert len(page.locator('#content').inner_text())>80,f'Deep screen {route} blank'
          assert not detail_errors,f'Deep screen {route} crashed: {detail_errors}'
      page.evaluate('''() => {state.screen=null;nav('mods');action('filters')}''')
      assert 'Explore filters' in page.locator('#modal').inner_text(), 'Filter sheet broken'
      page.evaluate('''() => action('close-sheet')''')
      assert not page.locator('#modal').inner_text(), 'Filter sheet cannot close'
      page.evaluate('''() => action('install:5')''')
      assert 'Review mod installation' in page.locator('#modal').inner_text(), 'Install review sheet missing'
      page.evaluate('''() => action('queue-mod:5')''')
      assert page.evaluate('state.downloadQueue.length')>0,'Demo queue interaction broken'
      page.close();browser.close()
    reference_geom=ROOT/'02_CONTRACT'/'browser-layout-golden.json'
    if update:
        reference_geom.write_text(json.dumps(geometry,indent=2)+'\n')
        print(f'BROWSER_REFERENCE_GOLDENS_UPDATED {len(geometry)} screenshots')
    else:
        ref=json.loads(reference_geom.read_text());assert len(ref)==len(geometry)
        for a,b in zip(ref,geometry):
            assert a['screen']==b['screen'] and a['viewport']==b['viewport']
            for k in ('device','status','header','content','bottom'):
                assert a[k] and b[k]
                for n,(v,w) in enumerate(zip(a[k],b[k])):
                    assert abs(v-w)<=2.0,f'GEOMETRY_DRIFT {a["screen"]} {k}[{n}] golden={v} current={w}'
            for anchor,baseline_box in a['anchors'].items():
                current_box=b['anchors'].get(anchor)
                assert (baseline_box is None)==(current_box is None),f'ANCHOR_PRESENCE_DRIFT {a["screen"]} {anchor}'
                if baseline_box:
                    for n,(v,w) in enumerate(zip(baseline_box,current_box)):
                        assert abs(v-w)<=2.0,f'ANCHOR_DRIFT {a["screen"]} {anchor}[{n}] golden={v} current={w}'
        print(f'BROWSER_REFERENCE_24_SCREENSHOT_AND_GEOMETRY_PASS screen_states={len(geometry)} avg_pixel_delta_max={max((z for _,_,z in results),default=0)}')
    print('BROWSER_STATIC_FALLBACK_AND_OPTIONAL_STEAM_PASS')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--update-goldens',action='store_true',help='intentional reference update ONLY')
    mode.add_argument('--verify',action='store_true')
    args=ap.parse_args();run(args.update_goldens)
