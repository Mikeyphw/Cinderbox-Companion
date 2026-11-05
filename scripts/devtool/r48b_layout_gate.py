#!/usr/bin/env python3
"""R48B source-only guard for real screenshot-derived compact header fixes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    header_path = root / 'app/src/main/java/com/sdvsync/ui/components/StardewTopAppBar.kt'
    try:
        header = header_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return ['missing shared top bar']
    required = (
        'BoxWithConstraints(modifier = Modifier.fillMaxWidth())',
        'val compact = maxWidth < 420.dp',
        'TopAppBar(',
        'if (!compact)',
        'Row { SteamLiveBadge(); actions() }',
        'if (compact)',
        'import androidx.compose.foundation.layout.ExperimentalLayoutApi',
        '@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)',
        'FlowRow(',
        'SteamLiveBadge()\n                        actions()',
        'horizontalArrangement = Arrangement.spacedBy(8.dp)',
        'verticalArrangement = Arrangement.spacedBy(4.dp)',
        'drawBehind',
    )
    for line in required:
        if line not in header:
            errors.append('compact header invariant missing: ' + line)
    if header.count('SteamLiveBadge()') != 2 or header.count('actions()') != 2:
        errors.append('Steam/action parity changed')
    if 'Modifier.clickable' in header or 'loginWithSavedSession' in header:
        errors.append('header must not invoke authentication')
    # The source guard complements, but never substitutes for, hosted runtime
    # screenshots and Android instrumentation on the exact PR-head commit.
    for p, patterns in {
        'app/src/main/java/com/sdvsync/ui/screens/HomeScreen.kt': (
            '"Your Cinderbox workspace"', '"Open operation center"',
        ),
        'app/src/main/java/com/sdvsync/ui/components/StardewBottomBar.kt': (
            'BottomTab.entries.forEach', 'role = Role.Tab',
        ),
        'app/src/androidTest/java/com/sdvsync/qualification/R48RealActivityDeviceTest.kt': (
            'realOfflineFiveTabNavigationAndPrivatePreviews', 'captureToImage()',
        ),
    }.items():
        try:
            content = (root / p).read_text(encoding='utf-8')
        except FileNotFoundError:
            errors.append('missing existing UI gate: ' + p)
            continue
        for token in patterns:
            if token not in content:
                errors.append('existing UI gate changed: ' + p + ': ' + token)
    policy = root / 'docs/security/M3_RELEASE_POLICY.json'
    if policy.exists():
        release = json.loads(policy.read_text(encoding='utf-8'))
        for key in ('release_enabled', 'publication_enabled', 'automatic_device_install', 'device_qualification_complete'):
            if release.get(key) is not False:
                errors.append('release policy must stay disabled: ' + key)
    else:
        errors.append('missing release policy')
    return errors


def main() -> int:
    errors = check()
    for e in errors:
        print('R48B_HEADER_REFUSED: ' + e)
    if errors:
        return 1
    print('R48B_COMPACT_HEADER_AND_RELEASE_POLICY_SOURCE_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
