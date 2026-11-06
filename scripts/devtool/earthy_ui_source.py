#!/usr/bin/env python3
"""UI-D01 host-only contrast, single-dark and release-policy source checks.

The historic filename is retained only for older CI callers. Earthy/Classic
palettes are not user-selectable or active. No emulator/device/Steam access.
"""
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
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def verify() -> dict:
    tokens = (THEME / 'CinderboxDarkTokens.kt').read_text()
    theme = (THEME / 'Theme.kt').read_text()
    activity = (ROOT / 'app/src/main/java/com/sdvsync/MainActivity.kt').read_text()
    settings = (ROOT / 'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt').read_text()
    preferences = (THEME / 'AppearancePreferences.kt').read_text()
    coordinator = (ROOT / 'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt').read_text()
    policy = json.loads((ROOT / 'docs/security/M3_RELEASE_POLICY.json').read_text())
    active_function = theme.split('fun SdvSyncTheme(', 1)[-1]
    frozen_tokens = {
        'Background': '#101915', 'Paper': '#1B2922', 'Paper2': '#22362B',
        'Ink': '#ECF5E9', 'Muted': '#ACBDB0', 'Line': '#324739',
        'Forest': '#8CD9A8', 'Accent': '#EEBC78', 'Hero': '#173D2D',
    }
    declared = dict(re.findall(r'val (\w+) = Color\(0xFF([0-9A-Fa-f]{6})\)', tokens))
    declared = {name: '#' + color.upper() for name, color in declared.items()}
    pairs = {
        'body_on_surface': ('Ink', 'Paper'),
        'body_on_background': ('Ink', 'Background'),
        'secondary_on_surface': ('Muted', 'Paper'),
        'accent_on_background': ('Forest', 'Background'),
        'attention_on_background': ('Accent', 'Background'),
    }
    checks = {
        'frozen_dark_colors': all(declared.get(k) == v for k, v in frozen_tokens.items()),
        'dark_color_scheme': 'val colorScheme = darkColorScheme(' in tokens,
        'effective_single_dark_scheme': 'colorScheme = CinderboxDarkTokens.colorScheme' in active_function,
        'approved_typography_and_shapes': 'typography = R44ProductTypography' in active_function and 'shapes = R44ProductShapes' in active_function,
        'no_legacy_theme_selection': all(x not in active_function for x in ('LightColorScheme', 'DarkColorScheme', 'EarthyLightColorScheme', 'EarthyDarkColorScheme', 'if (style', 'if (darkTheme')),
        'local_first_start': 'startDestination = "main"' in activity and 'startDestination = "home"' in activity,
        'active_theme_not_user_preference': 'SdvSyncTheme {' in activity and 'appearance.mode.resolve(' not in activity and 'appearanceStore.settings.collectAsState' not in activity,
        'more_has_fixed_dark_status': 'Dark · default' in settings and 'appearanceStore.setStyle(' not in settings and 'appearanceStore.setMode(' not in settings,
        'legacy_preferences_corruption_safe': 'ReplaceFileCorruptionHandler' in preferences and 'emptyPreferences()' in preferences,
        'release_and_device_qualification_disabled': all(policy.get(k) is False for k in ('release_enabled', 'publication_enabled', 'automatic_device_install', 'device_qualification_complete')),
        'game_update_fail_closed': 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coordinator and 'const val DEVICE_ACCEPTED: Boolean = false' in coordinator,
        'no_external_ui_art': not any(x in tokens for x in ('AssetManager', 'BitmapFactory', 'nexusmods.com', 'https://')),
    }
    ratios = {}
    for label, (fg, bg) in pairs.items():
        if fg in declared and bg in declared:
            ratios[label] = round(contrast(declared[fg], declared[bg]), 3)
        else:
            ratios[label] = 0.0
        checks['contrast_' + label] = ratios[label] >= 4.5
    paths = [THEME / 'CinderboxDarkTokens.kt', THEME / 'Theme.kt',
             THEME / 'AppearancePreferences.kt',
             ROOT / 'app/src/main/java/com/sdvsync/MainActivity.kt',
             ROOT / 'app/src/main/java/com/sdvsync/ui/screens/SettingsScreen.kt',
             ROOT / 'docs/security/M3_RELEASE_POLICY.json',
             ROOT / 'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    return {'schema_version': 1, 'producer': 'cinderbox-ui-d01-host',
            'source': 'checked-worktree', 'checks': checks,
            'contrast_ratios': ratios, 'source_sha256': hashes,
            'overall': 'PASS_HOST_STATIC' if all(checks.values()) else 'FAILED_HOST_STATIC',
            'not_performed': ['Android build', 'Android device instrumentation', 'UI screenshot comparison', 'release qualification']}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify()
    payload = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
    print(payload, end='')
    return 0 if result['overall'] == 'PASS_HOST_STATIC' else 1


if __name__ == '__main__':
    raise SystemExit(main())
