#!/usr/bin/env python3
"""UI-D02 native Devtool source contract: no privileged or network work."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PREFIX = Path('app/src/main/java/com/sdvsync/ui')
CHECKED_FILES = {
    'card': 'components/StardewCard.kt',
    'dialog': 'components/StardewDialog.kt',
    'top_bar': 'components/StardewTopAppBar.kt',
    'steam_status': 'components/SteamLiveBadge.kt',
    'empty_state': 'components/EmptyState.kt',
    'spinner': 'components/PixelLoadingSpinner.kt',
    'wizard': 'components/CinderboxWizardDialog.kt',
    'sparkle': 'components/SparkleOverlay.kt',
    'save_viewer': 'screens/SaveViewerScreen.kt',
}


def verify() -> dict:
    sources = {name: (ROOT/PREFIX/path).read_text(encoding='utf-8') for name, path in CHECKED_FILES.items()}
    contract = {
        'card_style_specific': 'if (earthy) MaterialTheme.colorScheme.surfaceContainerLow else MaterialTheme.colorScheme.surfaceContainerHigh' in sources['card'],
        'dialog_style_specific': 'if (earthy) MaterialTheme.colorScheme.surfaceContainerLow else MaterialTheme.colorScheme.surfaceContainerHigh' in sources['dialog'],
        'topbar_contrast': 'onPrimaryContainer' in sources['top_bar'] and 'TopAppBarDefaults.topAppBarColors' in sources['top_bar'],
        'steam_phase_preserved': all(s in sources['steam_status'] for s in ('Phase.CONNECTED', 'Phase.CONNECTING', 'Phase.AUTHENTICATING', 'Phase.RECONNECTING', 'Phase.OFFLINE')),
        'steam_classic_kept': 'else color' in sources['steam_status'] and 'else Color.White' in sources['steam_status'],
        'steam_no_new_network_request': 'loginWithSavedSession()' in sources['steam_status'] and 'if (earthy) statusTextColor' in sources['steam_status'],
        'empty_state_style_specific': 'palette = if (earthy)' in sources['empty_state'],
        'spinner_style_specific': 'if (earthy) MaterialTheme.colorScheme.tertiary else GoldBright' in sources['spinner'],
        'wizard_classic_kept': 'else GoldAmber' in sources['wizard'] and 'else SuccessGreen' in sources['wizard'],
        'sparkle_cancels_on_style_change': 'LaunchedEffect(earthy, earthyLight, earthyDark)' in sources['sparkle'],
        'save_viewer_classic_kept': 'else GoldAmber' in sources['save_viewer'],
        'device_synthetic_only': 'No real account, files, or device mutation' in (ROOT/'app/src/androidTest/java/com/sdvsync/qualification/EarthyComponentsDeviceTest.kt').read_text(),
    }
    policy = json.loads((ROOT/'docs/security/M3_RELEASE_POLICY.json').read_text())
    contract['release_still_disabled'] = all(policy.get(k) is False for k in ('release_enabled', 'device_qualification_complete', 'publication_enabled'))
    source_sha256 = {str(PREFIX/p): hashlib.sha256((ROOT/PREFIX/p).read_bytes()).hexdigest() for p in CHECKED_FILES.values()}
    return {
        'schema_version': 1, 'producer': 'cinderbox-ui-d02-source',
        'overall': 'PASS_SOURCE_CONTRACT' if all(contract.values()) else 'FAILED_SOURCE_CONTRACT',
        'checks': contract, 'source_sha256': source_sha256,
        'device_tests': 'NOT_RUN', 'android_build': 'NOT_RUN',
        'historical_m21_results_replaced': False, 'release_qualified': False, 'publication_allowed': False,
    }


if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result['overall'] == 'PASS_SOURCE_CONTRACT' else 1)
