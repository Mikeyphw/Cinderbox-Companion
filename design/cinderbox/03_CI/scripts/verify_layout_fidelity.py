#!/usr/bin/env python3
"""Pin original approval, palette-only dark conversion, and user's single-dark amendment.
Browser screenshot/anchor checker independently checks that layout did not drift.
"""
from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parents[2]
c=json.loads((ROOT/'02_CONTRACT/ux-contract.json').read_text())
ref=c['reference']
def read(name): return (ROOT/'01_REFERENCE'/name).read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
light=read('APPROVED_LIGHT_ORIGINAL_READONLY.html')
previous=read('APPROVED_DARK_PRE_SINGLE_THEME_READONLY.html')
dark=read('cinderbox-portrait-DARK.html')
assert sha(light)==ref['origin_sha256'], 'Original approval reference changed'
assert sha(previous)==ref['previous_dark_sha256'], 'Prior approved dark reference changed'
assert sha(dark)==ref['sha256'], 'Single-dark reference changed after signoff'
assert ref['sole_theme']=='dark'
source=dark.decode()
assert '<html lang="en" data-theme="dark">' in source
assert 'color-scheme: dark' in source
assert 'Dark · default' in source
assert 'theme:light' not in source and 'theme:dark' not in source
assert 'function renderTopBar()' in source and 'function top()' not in source
assert source.count('<section class="offline-screen"')>=5
assert 'steam:false' in source and "theme:'dark'" in source
print('APPROVED_REFERENCE_SINGLE_DARK_EXACT_HASH_AND_NO_ALTERNATE_THEMES_PASS')
