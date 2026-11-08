#!/usr/bin/env python3
"""Fail-closed no-network source contract for NEX-R2C native schema and optional live lane."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
API='app/src/main/java/com/sdvsync/mods/api/'
TEST='app/src/test/java/com/sdvsync/mods/api/'
FILES=(API+'NexusCatalogOperation.kt',API+'NexusModSource.kt',
       API+'NexusProviderIntegrity.kt',TEST+'NexusProviderIntegrityTest.kt',
       TEST+'NexR1CatalogContractTest.kt','scripts/devtool/nex_r2c_live_probe.py',
       'scripts/devtool/test_nex_r2c_live_probe.py',
       '.github/workflows/nex-r2c-provider-qualification.yml',
       'docs/devtool/NEX_R2C_LIVE_PROVIDER_CONTRACT.md',
       'docs/security/M3_RELEASE_POLICY.json')

def check(root:Path=ROOT)->list[str]:
    root=Path(root)
    contents={}
    for path in FILES:
        p=root/path
        if not p.is_file() or p.is_symlink():return ['NEX_R2C_MISSING_OR_SYMLINK:'+path]
        contents[path]=p.read_text(encoding='utf-8')
    cat,source,integrity=tuple(contents[k] for k in FILES[:3])
    smoke=contents['scripts/devtool/nex_r2c_live_probe.py']
    ci=contents['.github/workflows/nex-r2c-provider-qualification.yml']
    doc=contents['docs/devtool/NEX_R2C_LIVE_PROVIDER_CONTRACT.md']
    errors=[]
    checks={
      'graphql nested category': 'modCategory { name }' in cat and 'categoryName: category' not in cat,
      'graphql updatedAt': '                  updatedAt\n' in cat,
      'safe nested mapping': 'node.optJSONObject("modCategory")?.optString("name", "")' in source,
      'safe timestamp mapping': 'NexusProviderIntegrity.graphqlUpdatedAt(' in source,
      'bounded ISO date': 'fun graphqlUpdatedAt(raw: String?): Long' in integrity and
                          'java.time.Instant.parse(raw.trim())' in integrity,
      'mapped regression tests': 'providerQueryUsesNestedCategoryAndIsoUpdatedAt' in contents[FILES[4]] and
                                 'graphqlUpdatedAtAcceptsIso8601AndRejectsBadProviderDates' in contents[FILES[3]],
      'actual Kotlin query read by probe': 'query_from_source(root)' in smoke and
                            'document\\s*=\\s*' in smoke and 'SOURCE_GAME_PIN_DRIFT' in smoke,
      'secret from environment only': "os.environ.get('CINDERBOX_NEXUS_API_KEY', '')" in smoke and
                           'argparse.ArgumentParser' in smoke,
      'explicit opt-in network': 'def probe(' in smoke and 'def request_json(' in smoke,
      'bounded receipt': "'raw_provider_payload_included': False" in smoke and
                          "'native_app_navigation_verified': False" in smoke,
      'no auto live check on PR': 'if: github.event_name == \'workflow_dispatch\'' in ci and
                                  'CINDERBOX_NEXUS_API_KEY: ${{ secrets.CINDERBOX_NEXUS_API_KEY }}' in ci,
      'source and JVM job': 'test_nex_r2c_gate.py' in ci and
                   'test_nex_r2c_live_probe.py' in ci and ':app:testDebugUnitTest' in ci,
      'no duplicated emulator': 'android-emulator-runner' not in ci and 'assembleDebugAndroidTest' not in ci,
      'honest boundary documentation': 'not a live provider capture' in doc.lower() and
                                         'manual' in doc.lower() and 'not qualified' in doc.lower(),
    }
    for key,ok in checks.items():
        if not ok:errors.append('NEX_R2C_MISSING:'+key)
    policy=json.loads(contents['docs/security/M3_RELEASE_POLICY.json'])
    for flag in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        if policy.get(flag) is not False:errors.append('NEX_R2C_RELEASE_POLICY_DRIFT:'+flag)
    for field in ('WebView(', 'requestShizukuPermission(', 'installPackage(',
                  'startDownload(', 'Runtime.getRuntime('):
        if field in smoke+integrity:errors.append('NEX_R2C_UNSAFE_OPERATION:'+field)
    return errors

if __name__=='__main__':
    failures=check()
    if failures:
        print('\n'.join(failures));raise SystemExit(1)
    print('NEX_R2C_SCHEMA_AND_READ_ONLY_SOURCE_PASS_LIVE_UNQUALIFIED_UNTIL_OPT_IN')
