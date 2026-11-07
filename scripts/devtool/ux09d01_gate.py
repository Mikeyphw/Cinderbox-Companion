#!/usr/bin/env python3
"""UX09D01 replacement source and safety contract, default-size visual UX only."""
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
SCREENS={
 'mods':('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt','YOUR MOD LIBRARY'),
 'saves':('app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt','LOCAL & CLOUD'),
 'more':('app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt','SETTINGS & MORE'),
}

def check(root=ROOT):
 root=pathlib.Path(root)
 component=(root/'app/src/main/java/com/sdvsync/ui/components/CinderboxBrandTopBar.kt').read_text()
 assert component.count('fun CinderboxBrandTopBar(')==1,'UX09D01_SHARED_BRAND_MISSING'
 for required in ('Modifier.fillMaxWidth().height(49.dp)','testTag("cinderbox.shell.branded-topbar")',
   'Text("Cinderbox"','Dark.Mint','Dark.Ink','Dark.Forest','Text("Activity"',
   'testTag("cinderbox.shell.brand-activity")', 'onClick = onOpenOperationCenter'):
  assert required in component,'UX09D01_BAD_GLOBAL_HEADER:'+required
 assert 'onPrimaryAction' not in component and 'onSecondaryAction' not in component, 'UX09D01_MISLEADING_ACTIONS'
 assert 'Text("↓"' not in component and 'Text("♧"' not in component,'UX09D01_AMBIGUOUS_ICONS'
 for name,(rel,subtitle) in SCREENS.items():
  content=(root/rel).read_text()
  assert content.count('CinderboxBrandTopBar(')==1,'UX09D01_WRONG_HEADER_COUNT:'+name
  assert f'subtitle = "{subtitle}"' in content,'UX09D01_WRONG_SUBTITLE:'+name
  assert 'onOpenOperationCenter = onOpenOperationCenter' in content,'UX09D01_GLOBAL_ROUTE:'+name
 main=(root/'app/src/main/java/com/sdvsync/MainActivity.kt').read_text()
 assert 'enableEdgeToEdge(statusBarStyle = androidx.activity.SystemBarStyle.dark(android.graphics.Color.TRANSPARENT))' in main, 'UX09D01_LIGHT_STATUS_FOREGROUND_MISSING'
 assert 'WindowInsets.statusBars' in main,'UX09D01_STATUS_INSET_REMOVED'
 assert main.count('onOpenOperationCenter = { parentNavController.navigate("operation_center") }')>=4,'UX09D01_GLOBAL_NAV_WIRING'
 assert 'startDestination = "main"' in main and 'onConnectSteam' in main
 operations=(root/'app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt').read_text()
 for route_tag in ('testTag("cinderbox.screen.operation-center")',
                   'testTag("cinderbox.operation-center.back")'):
  assert route_tag in operations, 'UX09D01_OPERATION_CENTER_ROUTE_TAG_MISSING:'+route_tag
 assert 'StardewTopAppBar("Operation center"' in operations and 'onClick = onBack' in operations, 'UX09D01_OPERATIONS_BACK_CHANGED'
 mods=(root/SCREENS['mods'][0]).read_text()
 assert 'Text("Mods", color = Dark.Ink' in mods,'UX09D01_MODS_PAGE_TITLE'
 assert 'Text("Your mods", color = Dark.Ink' not in mods,'UX09D01_OLD_PAGE_TITLE'
 assert 'Text("Manage local mods")' in mods,'UX09D01_MANAGER_NOT_DISCOVERABLE'
 assert mods.count('testTag("cinderbox.mods.advanced")') == 1,'UX09D01_DUPLICATE_MANAGER_ACTION'
 assert 'ModsPanel("Advanced mod management"' not in mods,'UX09D01_BURIED_DUPLICATE'
 assert 'onClick = onOpenAdvancedMods' in mods,'UX09D01_MANAGER_ROUTE_NOT_WIRED'
 assert 'onOpenQueue' in mods and 'onBrowseMods' in mods,'UX09D01_MODS_ACTIONS_LOST'
 # Source contract cannot prove real click behavior; hosted instrumentation must.
 android=(root/'app/src/androidTest/java/com/sdvsync/ui/ux/UxNormalChromeTest.kt').read_text()
 for required in ('capture("mods"', 'capture("saves"', 'capture("more"',
  'WindowInsetsControllerCompat', 'isAppearanceLightStatusBars',
  '"cinderbox.mods.advanced"', '"cinderbox.screen.advanced-mods"',
  '"cinderbox.screen.operation-center"', '"cinderbox.operation-center.back"',
  'requireVisibleTag(', 'UX09D01_STAGE_FAILED:',
  'performScrollToNode(hasTestTag("cinderbox.mods.advanced"))',
  'checkGlobalActivityAndBack(', 'content_unique_colors',
  'UX09D01_BLANK_SCREEN_CONTENT'):
  assert required in android,'UX09D01_HOSTED_FUNCTIONAL_TEST_MISSING:'+required
 assert 'font in 0.98f..1.02f' in android and '.put("font_percent", 100)' in android
 runner=(root/'scripts/devtool/ux09d01_emulator_ci.sh').read_text()
 assert 'settings put system font_scale 1.0' in runner and 'UX09D01_PHYSICAL_DEVICE_REFUSED' in runner
 workflow=(root/'.github/workflows/cinderbox-ux09d01-normal-visual.yml').read_text()
 assert workflow.count("- 'app/src/main/java/com/sdvsync/MainActivity.kt'") == 2, 'UX09D01_MISSING_MAIN_TRIGGER'
 assert workflow.count("- 'app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt'") == 2, 'UX09D01_MISSING_OPERATIONS_TRIGGER'
 report=(root/'scripts/devtool/ux09d01_report.py').read_text()
 assert "'native_goldens_approved': False" in report and 'status_icons_light' in report
 assert 'zlib.crc32(tag + payload)' in report and 'png_color_sample(' in report, 'UX09D01_PNG_VALIDATOR_MISSING'
 assert 'UX09D01_BLANK_CONTENT:' in report and 'UX09D01_PIXEL_RECEIPT_MISMATCH:' in report, 'UX09D01_IMAGE_GUARDS_MISSING'
 policy=json.loads((root/'docs/security/M3_RELEASE_POLICY.json').read_text())
 for key in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
  assert policy[key] is False,'UX09D01_RELEASE_POLICY_CHANGED:'+key
 live=(root/'app/src/main/java/com/sdvsync/download/R43BUpdateCoordinator.kt').read_text()
 for token in ('const val LIVE_UPDATES_ENABLED: Boolean = false', 'const val DEVICE_ACCEPTED: Boolean = false'):
  assert token in live,'UX09D01_LIVE_GATE_CHANGED'
 contract=json.loads((root/'design/cinderbox/02_CONTRACT/ux-contract.json').read_text())
 reference=root/'design/cinderbox'/contract['reference']['path']
 assert contract['reference']['sole_theme']=='dark' and contract['screenshot_cases']['count']==24,'UX09D01_APPROVED_CONTRACT_CHANGED'
 assert reference.is_file() and hashlib.sha256(reference.read_bytes()).hexdigest()==contract['reference']['sha256'],'UX09D01_REFERENCE_DRIFT'
 print('UX09D01_REPLACEMENT_NORMAL_UI_AND_FUNCTIONAL_SOURCE_PASS')
 return True

if __name__=='__main__':
 try: check()
 except Exception as error:
  print('UX09D01_SOURCE_REFUSED:'+str(error),file=sys.stderr)
  raise SystemExit(1)
