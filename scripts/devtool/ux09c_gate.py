#!/usr/bin/env python3
"""Fail-closed UX-09C01 source, color contrast, native semantics and safety gate."""
from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REQUIRED=(
 'app/src/androidTest/java/com/sdvsync/ui/ux/UxNativeAccessibilityTest.kt',
 'scripts/devtool/ux09c_emulator_ci.sh','scripts/devtool/ux09c_report.py',
 '.github/workflows/cinderbox-ux09c01-accessibility.yml',
 'docs/security/M3_RELEASE_POLICY.json',
 'app/src/main/java/com/sdvsync/ui/theme/CinderboxDarkTokens.kt',
 'app/src/main/java/com/sdvsync/mods/GameSessionSafety.kt',
 'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt',
 'design/cinderbox/02_CONTRACT/ux-contract.json',
)
FORBIDDEN=('startDownload(', 'restoreBackup(', 'deleteRecursively(', 'forceSync(',
           'requestShizukuPermission(', 'setFileAccessMode(', 'setSession(',
           'getExternalStorageDirectory(', '/storage/emulated/0/', 'Runtime.getRuntime(')

def source(root:Path,name:str)->str:
 p=root/name
 assert p.is_file() and not p.is_symlink(),'UX09C_MISSING_OR_SYMLINK:'+name
 return p.read_text()

def brightness(rgb:str)->float:
 channels=[int(rgb[i:i+2],16)/255 for i in (0,2,4)]
 linear=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
 return sum(v*k for v,k in zip(linear,(0.2126,0.7152,0.0722)))

def ratio(a:str,b:str)->float:
 x,y=brightness(a),brightness(b)
 return (max(x,y)+0.05)/(min(x,y)+0.05)

def check(root:Path=ROOT)->dict:
 root=Path(root)
 content={n:source(root,n) for n in REQUIRED}
 test,runner,report,workflow=(content[n] for n in REQUIRED[:4])
 assert 'createAndroidComposeRule<MainActivity>()' in test
 for method in ('captureFiveTabsAt200PercentFont','largeTextPreservesSteamLockAndDeepBack',
                'searchImeKeepsOfflineModsAccessible'):
  assert test.count('@Test fun '+method+'()')==1,'UX09C_TEST_MISSING:'+method
 for tag in ('cinderbox.screen.home','cinderbox.screen.game','cinderbox.screen.saves',
             'cinderbox.screen.mods','cinderbox.screen.more','cinderbox.more.help',
             'cinderbox.mods.search','cinderbox.shell.bottomnav'):
  assert '"'+tag+'"' in test,'UX09C_MISSING_ACTUAL_ROUTE:'+tag
 for token in ('b.width >= 96f && b.height >= 96f','performTextInput(',
               'Cloud · Locked','Connect Steam to download','Espresso.pressBack()',
               'UX09C_BLANK_COMPOSE_FRAME','real_offline_main_activity',
               'cinderbox.more.nexus','assertIsNotEnabled()','hasSetTextAction()',
               'ux09c_unsaved_ime_fixture','performScrollToNode(hasText('):
  assert token in test,'UX09C_MISSING_A11Y_ASSERTION:'+token
 for forbidden in FORBIDDEN:
  assert forbidden not in test,'UX09C_FORBIDDEN_SIDE_EFFECT:'+forbidden
 assert 'UX09C_PHYSICAL_DEVICE_REFUSED' in runner
 for token in ('wm density 320','font_scale 2.0','786x1704','720x1600',
               'OK (3 tests)','svc wifi disable','svc data disable',
               'UX09C_FONT_SCALE_NOT_SET','UX09C_TEST_FAILURE_RECEIPT_',
               'UX09C_HOSTED_DIAGNOSTIC','raw_device_log_included',
               'UX09C_INSTRUMENTATION_FAILED_WITH_SANITIZED_RECEIPT'):
  assert token in runner,'UX09C_HOST_DRIVER_MISSING:'+token
 for token in ("'actual_offline_screenshots':10", "'native_goldens_approved':False",
               "'real_steam_authentication_qualified':False", "'release_enabled':False",
               "'physical_device_qualified':False", 'UX09C_WRONG_PNG_SIZE',
               'UX09C_TARGET_TOO_SMALL'):
  assert token in report,'UX09C_REPORT_GUARD_MISSING:'+token
 assert 'api-level: 36' in workflow and 'scripts/devtool/ux09c_emulator_ci.sh' in workflow
 assert 'scripts/devtool/ux09c_gate.py' in workflow and 'if: always()' in workflow
 assert 'permissions:\n  contents: read' in workflow
 assert './gradlew' in workflow and './gradlew' not in runner
 theme=content[REQUIRED[5]]
 colors=dict(re.findall(r'val\s+(\w+)\s*=\s*Color\(0xFF([0-9A-Fa-f]{6})\)',theme))
 assert set(('Background','Paper','Ink','Muted','Faint','Forest','Mint'))<=set(colors),'UX09C_THEME_TOKEN_MISSING'
 checks={'main_text_on_background':('Ink','Background'),
         'muted_on_paper':('Muted','Paper'),
         'faint_on_paper':('Faint','Paper'),
         'green_on_mint':('Forest','Mint')}
 contrasts={name:round(ratio(colors[a],colors[b]),2) for name,(a,b) in checks.items()}
 assert all(value>=4.5 for value in contrasts.values()),'UX09C_LOW_COLOR_CONTRAST:'+repr(contrasts)
 policy=json.loads(content[REQUIRED[4]])
 for field in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
  assert policy[field] is False,'UX09C_POLICY_DRIFT:'+field
 assert ': Boolean = false' in content[REQUIRED[6]],'UX09C_LIVE_WRITE_POLICY_DRIFT'
 coord=content[REQUIRED[7]]
 assert 'const val LIVE_UPDATES_ENABLED: Boolean = false' in coord
 assert 'const val DEVICE_ACCEPTED: Boolean = false' in coord
 contract=json.loads(content[REQUIRED[8]])
 assert contract['reference']['sole_theme']=='dark' and contract['screenshot_cases']['count']==24
 ref=root/'design/cinderbox'/contract['reference']['path']
 assert ref.is_file() and not ref.is_symlink()
 assert hashlib.sha256(ref.read_bytes()).hexdigest()==contract['reference']['sha256'],'UX09C_REFERENCE_DRIFT'
 return {'result':'UX09C01_A11Y_SOURCE_PASS','target_min_dp':48,
         'font_scale':2.0,'viewports_dp':[393,360],'offline_actual_screenshot_candidates':10,
         'color_contrast_ratios':contrasts,'native_goldens_approved':False,'release_enabled':False}
if __name__=='__main__':
 try:print(json.dumps(check(),sort_keys=True))
 except (AssertionError,OSError,ValueError,KeyError) as e:
  print('UX09C01_SOURCE_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(1)
