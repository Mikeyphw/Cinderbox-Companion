#!/usr/bin/env python3
"""Fail-closed source gate for future Android Compose parity work. Not a substitute for device screenshot tests.
Run from ANY cwd: python design/cinderbox/03_CI/scripts/check_native_parity.py --repo-root .
"""
import argparse, pathlib, json, re, sys
P=pathlib.Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('--repo-root',required=True);args=a.parse_args()
repo=pathlib.Path(args.repo_root).resolve();contract=json.loads((P/'02_CONTRACT/ux-contract.json').read_text())
source=repo/'app/src/main/java'; tests=repo/'app/src/androidTest/java'
assert source.exists() and tests.exists(), 'Android app and androidTest sources missing'
all_source='\n'.join(f.read_text(errors='replace') for f in source.rglob('*.kt'))
all_tests='\n'.join(f.read_text(errors='replace') for f in tests.rglob('*.kt'))
required_tags=sum(contract['ui_semantics'].values(),[])
not_found=[t for t in required_tags if t not in all_source]
if not_found:
 print('NATIVE_UI_TEST_TAGS_MISSING:',', '.join(not_found));sys.exit(1)
# Require explicit named Android UI tests; dead constants cannot make this pass.
needed_tests=['darkDefaultHome','optionalSteamFirstLaunch','offlineLocalSavesRemainAvailable','steamDownloadsLockedWithoutAuthentication','steamCloudLockedWithoutAuthentication','modsDiscoverAndSections','allFiveBottomTabs','darkThemeTokenParity','backNavigationAndSheets']
missing=[n for n in needed_tests if not re.search(r'fun\s+'+n+r'\s*\(',all_tests)]
if missing:
 print('NATIVE_ANDROID_UI_TESTS_MISSING:',', '.join(missing));sys.exit(1)
# Tokens should be native Compose Color(0xFF...) values, not a claim based on the HTML CSS.
missing_colors=[k for k,v in contract['dark_palette'].items() if f'0xFF{v[1:].upper()}'.upper() not in all_source.upper()]
if missing_colors:
 print('NATIVE_DARK_TOKENS_MISSING:', ', '.join(missing_colors));sys.exit(1)
# Critical permissions and release policies must remain fail-closed across UI work.
safety=(repo/'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt').read_text()
assert 'permitsLiveBulkWrite' in safety and ': Boolean = false' in safety, 'Unexpected write gate change'
policy=json.loads((repo/'docs/security/M3_RELEASE_POLICY.json').read_text())
for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
 assert policy[key] is False, f'Safety release gate changed: {key}'
print('NATIVE_UI_SOURCE_PARITY_GATE_PASS',len(required_tags),'tags',len(needed_tests),'instrumentation test names')
