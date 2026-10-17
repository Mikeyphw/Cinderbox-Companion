#!/usr/bin/env python3
"""UI-D01 offline, source-bound palette/policy checks. No Android build or device access."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / 'app/src/main/java/com/sdvsync/ui/theme'


def contrast(a: str, b: str) -> float:
    def luminance(c: str) -> float:
        assert re.fullmatch(r'#[0-9A-Fa-f]{6}', c), c
        channels = [int(c[i:i+2], 16) / 255 for i in (1, 3, 5)]
        values = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055)**2.4 for v in channels]
        return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]
    l1, l2 = sorted((luminance(a), luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def verify() -> dict:
    schemes = (THEME/'EarthyColorSchemes.kt').read_text()
    pref = (THEME/'AppearancePreferences.kt').read_text()
    theme = (THEME/'Theme.kt').read_text()
    activity = (ROOT/'app/src/main/java/com/sdvsync/MainActivity.kt').read_text()
    settings = (ROOT/'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt').read_text()
    policy = json.loads((ROOT/'docs/security/M3_RELEASE_POLICY.json').read_text())
    checks = {
        'palettes_declared': 'EarthyLightColorScheme' in schemes and 'EarthyDarkColorScheme' in schemes,
        'classic_is_default': 'val style: AppearanceStyle = AppearanceStyle.CLASSIC' in pref,
        'system_brightness_default': 'val mode: AppearanceMode = AppearanceMode.SYSTEM' in pref,
        'invalid_style_safe': '?: AppearanceStyle.CLASSIC' in pref,
        'invalid_mode_safe': '?: AppearanceMode.SYSTEM' in pref,
        'private_corruption_handler': 'ReplaceFileCorruptionHandler' in pref and 'emptyPreferences()' in pref,
        'app_theme_reactive': 'appearanceStore.settings.collectAsState' in activity,
        'settings_offline': 'appearanceStore.setStyle' in settings and 'appearanceStore.setMode' in settings,
        'classic_remains_supported': 'style: AppearanceStyle = AppearanceStyle.CLASSIC' in theme,
        'ui_has_no_mod_art_assets': not any(x in schemes for x in ('AssetManager', 'BitmapFactory', 'piskel', 'nexusmods.com')),
        'publication_still_disabled': all(policy.get(k) is False for k in ('release_enabled', 'device_qualification_complete', 'publication_enabled')),
    }
    measured_pairs = {
        'earthy_light_body_on_surface': ('#342C26','#E5DBC6'),
        'earthy_dark_body_on_surface': ('#F1E7D5','#302B25'),
        'earthy_light_primary_button': ('#F8F3E8','#3F5744'),
        'earthy_dark_primary_button': ('#1A2820','#A8BBA0'),
        'earthy_light_secondary_button': ('#FFF2E3','#604B3B'),
        'earthy_dark_secondary_button': ('#33271F','#C9B49F'),
        'earthy_light_tertiary_button': ('#FFF3EA','#8A5237'),
        'earthy_dark_tertiary_button': ('#412719','#D8AA87'),
    }
    ratios = {k: round(contrast(*pair), 3) for k, pair in measured_pairs.items()}
    for label, (fg, bg) in measured_pairs.items():
        assert f'0xFF{fg[1:]}' in schemes and f'0xFF{bg[1:]}' in schemes, label
        checks[f'contrast_{label}'] = ratios[label] >= 4.5
    files = [THEME/'AppearancePreferences.kt', THEME/'EarthyColorSchemes.kt', THEME/'EarthyDesignTokens.kt', THEME/'Theme.kt', ROOT/'app/src/main/java/com/sdvsync/MainActivity.kt', ROOT/'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt']
    sha_map = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    return {'schema_version': 1, 'producer': 'cinderbox-ui-d01-host', 'source': 'checked-worktree', 'checks': checks, 'contrast_ratios': ratios, 'source_sha256': sha_map, 'overall': 'PASS_HOST_STATIC' if all(checks.values()) else 'FAILED_HOST_STATIC', 'not_performed': ['Android build', 'Android device instrumentation', 'UI screenshot comparison', 'release qualification']}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify()
    encoded = json.dumps(result, indent=2, sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end='')
    return 0 if result['overall'] == 'PASS_HOST_STATIC' else 1


if __name__ == '__main__':
    raise SystemExit(main())
