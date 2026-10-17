#!/usr/bin/env python3
"""Source-bound UI-D03 accessibility checks. No device, network, installs or game data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from earthy_ui_source import contrast

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = Path('app/src/main/java/com/sdvsync/ui/components')
THEME = Path('app/src/main/java/com/sdvsync/ui/theme/EarthyColorSchemes.kt')
TEST = Path('app/src/androidTest/java/com/sdvsync/qualification/EarthyD03AccessibilityDeviceTest.kt')

# Validate real Kotlin scheme tokens, rather than independently hardcoding desired ratios.
PAIRS = (('primary','onPrimary'), ('primaryContainer','onPrimaryContainer'),
         ('secondary','onSecondary'), ('tertiary','onTertiary'),
         ('background','onBackground'), ('surface','onSurface'),
         ('surfaceVariant','onSurfaceVariant'), ('error','onError'))

def parse_colors(source: str) -> dict:
    named = dict(re.findall(r'^private val (\w+) = Color\(0xFF([0-9A-Fa-f]{6})\)',source,re.M))
    schemes = {}
    for mode,func in (('light','lightColorScheme'),('dark','darkColorScheme')):
        match = re.search(r'Earthy'+mode.capitalize()+r'ColorScheme\s*=\s*'+func+r'\(\n(.*?)\n\)',source,re.S)
        if not match:
            raise ValueError('Missing Earthy '+mode+' Kotlin scheme')
        values = dict(re.findall(r'^\s+(\w+) = (Color\(0xFF[0-9A-Fa-f]{6}\)|Color\.(?:White|Black)|[A-Za-z]+),?$',match.group(1),re.M))
        resolved = {}
        for key,value in values.items():
            direct=re.fullmatch(r'Color\(0xFF([0-9A-Fa-f]{6})\)',value)
            hexval = direct.group(1) if direct else ({'Color.White':'FFFFFF','Color.Black':'000000'}.get(value) or named.get(value))
            if hexval: resolved[key]='#'+hexval.upper()
        schemes[mode]=resolved
    return schemes

def verify() -> dict:
    src=(ROOT/THEME).read_text()
    nav=(ROOT/COMPONENTS/'StardewBottomBar.kt').read_text()
    prog=(ROOT/COMPONENTS/'PixelProgressBar.kt').read_text()
    spinner=(ROOT/COMPONENTS/'PixelLoadingSpinner.kt').read_text()
    device=(ROOT/TEST).read_text()
    policy=json.loads((ROOT/'docs/security/M3_RELEASE_POLICY.json').read_text())
    schemes=parse_colors(src)
    ratios={}
    checks={
        'navigation_selectable_group':'.selectableGroup()' in nav,
        'tab_selected_role_semantics':'selectable(selected = selected, role = Role.Tab' in nav,
        'tab_touch_area_56dp':'.heightIn(min = 56.dp)' in nav,
        'progress_accessible_range':'progressBarRangeInfo = ProgressBarRangeInfo(progress.coerceIn(0f, 1f), 0f..1f)' in prog,
        'spinner_status_description':'stateDescription = loadingStatus' in spinner,
        'responsive_synthetic_preview':'Modifier.width(320.dp)' in device and 'fontScale = 1.6f' in device,
        'screenshot_test_light_dark':'daylightScreenshotAt320DpAnd160PercentFont' in device and 'nighttimeScreenshotAt320DpAnd160PercentFont' in device,
        'synthetic_no_account_data':'No Steam identity, save files, installed game, network access' in device,
        'only_private_test_png':'target.openFileOutput(filename, Context.MODE_PRIVATE)' in device,
        'release_still_disabled':all(policy.get(k) is False for k in ('release_enabled','device_qualification_complete','publication_enabled')),
    }
    for mode in ('light','dark'):
        for bg,fg in PAIRS:
            pair=(schemes[mode].get(fg),schemes[mode].get(bg))
            key=f'{mode}_{fg}_on_{bg}'
            ratios[key]=round(contrast(*pair),3) if all(pair) else None
            checks['contrast_'+key]= ratios[key] is not None and ratios[key] >= 4.5
    files=[THEME,TEST,COMPONENTS/'StardewBottomBar.kt',COMPONENTS/'PixelProgressBar.kt',COMPONENTS/'PixelLoadingSpinner.kt',Path('app/src/main/res/values/strings.xml')]
    return {
        'schema_version':1, 'producer':'cinderbox-ui-d03-accessibility-source',
        'overall':'PASS_HOST_STATIC' if all(checks.values()) else 'FAILED_HOST_STATIC',
        'checks':checks,'contrast_ratios':ratios,
        'source_sha256':{str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
        'android_build':'NOT_RUN','device_tests':'NOT_RUN','screenshots':'NOT_CAPTURED',
        'historical_m21_results_replaced':False,'release_qualified':False,'publication_allowed':False,
    }

if __name__=='__main__':
    outcome=verify()
    print(json.dumps(outcome,indent=2,sort_keys=True))
    raise SystemExit(0 if outcome['overall']=='PASS_HOST_STATIC' else 1)
