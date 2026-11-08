#!/usr/bin/env python3
"""NEX-R2B read-only provider boundary checks; no Nexus token or device required."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
API = 'app/src/main/java/com/sdvsync/mods/api/'
FIX = 'scripts/devtool/fixtures/nex_r2b/'


def check(root: Path = ROOT) -> list[str]:
    root = Path(root)
    errors = []
    def read(path: str) -> str:
        dest = root / path
        if not dest.is_file() or dest.is_symlink():
            raise ValueError('MISSING_OR_SYMLINK:' + path)
        return dest.read_text(encoding='utf-8')
    provider = read(API+'NexusModSource.kt')
    integrity = read(API+'NexusProviderIntegrity.kt')
    test = read('app/src/test/java/com/sdvsync/mods/api/NexusProviderIntegrityTest.kt')
    doc = read('docs/devtool/NEX_R2B_PROVIDER_CONTRACT.md')
    ci = read('.github/workflows/nex-r2b-provider-integrity.yml')
    policy = json.loads(read('docs/security/M3_RELEASE_POLICY.json'))
    required = {
        'strict graphql ids': 'NexusProviderIntegrity.positiveId(node.opt("modId"))' in provider,
        'strict graphql count': 'NexusProviderIntegrity.totalCount(data.opt("totalCount"))' in provider,
        'provider-owned pagination': 'NexusProviderIntegrity.hasMore(offset, nodes.length(), totalCount)' in provider,
        'v1 details fail closed': 'NexusProviderIntegrity.positiveId(json.opt("mod_id"))' in provider,
        'file ids fail closed': 'NexusProviderIntegrity.positiveId(file.opt("file_id"))' in provider,
        'unknown category not main': 'NexusProviderIntegrity.fileCategory(' in provider and
           'file.optBoolean("is_primary", false)' in provider,
        'bounded timestamp': 'NexusProviderIntegrity.epochSecondsToMillis(' in provider,
        'positive ids': 'fun positiveId(' in integrity,
        'count': 'fun totalCount(' in integrity,
        'pagination': 'fun hasMore(' in integrity,
        'file category': '"UNSPECIFIED"' in integrity,
        'negative JVM tests': 'invalidAnd' not in test and 'validAndInvalidModIdentifiers' in test,
        'hosted JVM': 'NexusProviderIntegrityTest' in ci and ':app:testDebugUnitTest' in ci,
        'no duplicated emulator': 'android-emulator-runner' not in ci and 'assembleDebugAndroidTest' not in ci,
        'evidence honesty': 'not live' in doc.lower() and 'synthetic' in doc.lower(),
    }
    for label, good in required.items():
        if not good: errors.append('NEX_R2B_MISSING:'+label)
    for k in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        if policy.get(k) is not False: errors.append('NEX_R2B_RELEASE_POLICY_DRIFT:'+k)
    for disallowed in ('WebView(', 'requestShizukuPermission(', 'startDownload(', 'installPackage(',
                       'getNexusApiKey(', 'Runtime.getRuntime('):
        if disallowed in integrity + test: errors.append('NEX_R2B_UNSAFE_ADDITION:'+disallowed)
    for name in ('graphql_browse.schema_shaped.json', 'v1_files.schema_shaped.json'):
        obj = json.loads(read(FIX+name))
        if obj.get('fixture_kind') != 'synthetic_schema_shaped_not_live_nexus':
            errors.append('NEX_R2B_FIXTURE_PROVENANCE:'+name)
    browser = json.loads(read(FIX+'graphql_browse.schema_shaped.json'))
    nodes = browser['data']['mods']['nodes']
    if browser['data']['mods']['totalCount'] <= len(nodes) or not any(n.get('modId') is None for n in nodes):
        errors.append('NEX_R2B_BROWSE_ADVERSARIAL_FIXTURE_DRIFT')
    files = json.loads(read(FIX+'v1_files.schema_shaped.json'))['files']
    if not any(f.get('category_name') is None and f.get('is_primary') is False for f in files):
        errors.append('NEX_R2B_FILE_CATEGORY_FIXTURE_DRIFT')
    if not any(f.get('file_id') == 0 for f in files):
        errors.append('NEX_R2B_FILE_ID_FIXTURE_DRIFT')
    return errors


def main() -> int:
    try: errors = check()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('NEX_R2B_GATE_REFUSED:'+str(exc))
        return 1
    if errors:
        for e in errors: print(e)
        return 1
    print('NEX_R2B_PROVIDER_BOUNDARY_SOURCE_PASS_SYNTHETIC_FIXTURES_NOT_LIVE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
