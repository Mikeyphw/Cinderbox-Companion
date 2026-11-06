#!/usr/bin/env python3
"""UX09B3 fail closed source gates; NEVER count fixtures as Steam authentication."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=(
  'app/src/androidTest/java/com/sdvsync/ui/ux/UxNativeFixtureCaptureTest.kt',
  'scripts/devtool/ux09b3_emulator_ci.sh','scripts/devtool/ux09b3_report.py',
  '.github/workflows/cinderbox-ux09b3-presentation-fixtures.yml',
  'design/cinderbox/02_CONTRACT/ux-contract.json',
  'design/cinderbox/02_CONTRACT/browser-layout-golden.json',
  'docs/security/M3_RELEASE_POLICY.json',
  'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt',
  'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',
  'app/src/main/java/com/sdvsync/ui/screens/ApprovedGameScreen.kt',
  'app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt',
  'app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt',
)
UNSAFE=(
 'restoreBackup(', 'deleteRecursively(', 'startDownload(',
 'requestShizukuPermission(', 'setFileAccessMode(', 'forceSync(',
 'Runtime.getRuntime(', 'getExternalStorageDirectory(',
 'setSession(', 'saveCredentials(', 'steamAuthenticator.login(',
 'getSharedPreferences(', 'performLongClick(', '/storage/emulated/0/'
)
CASES=('game-steam-connected','saves-cloud-connected','mod-detail')

def source(root:Path,name:str)->str:
 p=root/name
 assert p.is_file() and not p.is_symlink(), 'UX09B3_MISSING_OR_SYMLINK:'+name
 return p.read_text()

def check(root:Path=ROOT)->dict:
 root=Path(root)
 for name in FILES:source(root,name)
 fixture=source(root,FILES[0]);runner=source(root,FILES[1]);report=source(root,FILES[2]);wf=source(root,FILES[3])
 assert 'createComposeRule()' in fixture and 'createAndroidComposeRule<MainActivity>()' not in fixture
 assert fixture.count('@Test fun captureGameSteamConnectedUiPreview()')==1
 assert fixture.count('@Test fun captureSavesCloudConnectedUiPreviewWithoutCloudAccess()')==1
 assert fixture.count('@Test fun captureModDetailWithInMemoryCatalogExample()')==1
 assert 'ApprovedGameScreen(' in fixture and 'ApprovedSavesScreen(' in fixture
 assert 'ApprovedModDetailContent(' in fixture and 'ModRequirementsAssessor.assess(fixture, null)' in fixture
 assert fixture.count('isSteamConnected = true')==2
 for c in CASES:assert '"'+c+'"' in fixture, 'UX09B3_CASE_MISSING:'+c
 for fragment in UNSAFE:assert fragment not in fixture, 'UX09B3_UNSAFE_INSTRUMENTATION:'+fragment
 for keyword in ('real_steam_authentication','real_steam_entitlement','real_cloud_access',
                 'provider_catalog_verified','production_state_mutated'):
  assert '.put("'+keyword+'", false)' in fixture,'UX09B3_FALSE_EVIDENCE_MISSING:'+keyword
 assert 'pictureUrl = null' in fixture and 'sourceId = "ux09b3-test-only"' in fixture
 assert 'UX09B3_PHYSICAL_DEVICE_REFUSED' in runner
 assert 'bash scripts/devtool/ux09b2_emulator_ci.sh' in runner
 assert 'OK (3 tests)' in runner and 'wm density 320' in runner
 assert 'UX09B3_INVALID_FIXTURE_CLAIM' in report and 'UX09B3_DIFFERENT_SOURCE' in report
 # Native image liveness must be proved twice: after Compose root rendering
 # and by independently inspecting the captured PNG in the host report.
 for invariant in ('rule.onRoot().captureToImage()', 'UX09B3_COMPOSE_ROOT_BLANK',
                   'UX09B3_BLANK_DISPLAY_CAPTURE', 'display_content_nonblank',
                   'display_sampled_unique_colors', 'display_capture_attempt'):
  assert invariant in fixture, 'UX09B3_MISSING_NATIVE_PIXEL_GUARD:'+invariant
 for invariant in ('def visible_native_frame(', 'UX09B3_BLANK_NATIVE_FRAME',
                   'independentDiversity=visible_native_frame(n,case)',
                   "'display_content_nonblank':True"):
  assert invariant in report, 'UX09B3_MISSING_HOST_PIXEL_GUARD:'+invariant
 for claim in ("'full_24_case_parity_verified':False","'native_goldens_approved':False",
               "'actual_real_activity_cases':21","'isolated_preview_fixture_cases':3",
               "'real_steam_auth_and_entitlement_qualified':False"):
  assert claim in report,'UX09B3_CLAIM_DRIFT:'+claim
 assert 'api-level: 36' in wf and 'scripts/devtool/ux09b3_emulator_ci.sh' in wf
 assert 'if: always()' in wf and 'scripts/devtool/ux09b2_gate.py' in wf
 assert 'attempt in 1 2 3' in wf and 'permissions:\n  contents: read' in wf
 contract=json.loads(source(root,FILES[4]));ref=root/'design/cinderbox'/contract['reference']['path']
 assert ref.is_file() and not ref.is_symlink()
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==contract['reference']['sha256'], 'UX09B3_APPROVED_REFERENCE_DRIFT'
 assert contract['reference']['sole_theme']=='dark' and contract['screenshot_cases']['count']==24
 assert len(json.loads(source(root,FILES[5])))==24
 policy=json.loads(source(root,FILES[6]));
 for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
  assert policy[key] is False, 'UX09B3_RELEASE_POLICY_DRIFT:'+key
 assert ': Boolean = false' in source(root,FILES[7])
 coord=source(root,FILES[8]);assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coord
 assert 'const val DEVICE_ACCEPTED: Boolean = false' in coord
 for idx,n in ((9,'ApprovedGameScreen('),(10,'ApprovedSavesScreen('),(11,'ApprovedModDetailContent(')):
  assert n in source(root,FILES[idx]), 'UX09B3_PRODUCTION_CONTENT_API_DRIFT'
 return {'result':'UX09B3_PRESENTATION_FIXTURE_SOURCE_PASS',
   'real_activity_screens':21,'fixture_only_screen_previews':3,'parity_approved':False,
   'entitlement_qualified':False,'release_enabled':False}

if __name__=='__main__':
 try:print(json.dumps(check(),sort_keys=True))
 except (AssertionError,KeyError,OSError,ValueError) as e:
  print('UX09B3_SOURCE_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(1)
