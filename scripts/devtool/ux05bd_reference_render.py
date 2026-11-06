#!/usr/bin/env python3
"""Render approved, immutably pinned HTML mod-detail at an exact viewport.

Browser-only reference, not a native screenshot and not a release/physical-device gate.
Never rewrites the approved HTML or its committed screenshots.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'design/cinderbox/01_REFERENCE/cinderbox-portrait-DARK.html'
CONTRACT=ROOT/'design/cinderbox/02_CONTRACT/ux-contract.json'

def run(width:int,height:int,out:Path)->None:
    assert (width,height) in {(393,852),(360,800)},'UX05BD_UNEXPECTED_REFERENCE_VIEWPORT'
    source=HTML.read_bytes()
    contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
    assert hashlib.sha256(source).hexdigest()==contract['reference']['sha256'], 'UX05BD_HTML_REFERENCE_DRIFT'
    assert contract['reference']['sole_theme']=='dark'
    out.parent.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1,reduced_motion='reduce')
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_content(source.decode('utf-8'),wait_until='load')
        page.evaluate('nav("mods");state.activeMod="1";state.screen="moddetail";render(true)')
        assert not errors,'UX05BD_HTML_RUNTIME_ERROR'
        assert page.locator('.bottom button').count()==5
        assert 'Expanded Valley' in page.locator('#content').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1,'UX05BD_HTML_HORIZONTAL_OVERFLOW'
        page.screenshot(path=str(out),animations='disabled')
        page.close();browser.close()
    print(f'UX05BD_APPROVED_HTML_REFERENCE_RENDER_PASS {width}x{height} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}')

if __name__=='__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('--width',type=int,required=True)
    cli.add_argument('--height',type=int,required=True)
    cli.add_argument('--output',type=Path,required=True)
    args=cli.parse_args()
    run(args.width,args.height,args.output)
