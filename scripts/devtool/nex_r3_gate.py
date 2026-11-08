#!/usr/bin/env python3
"""NEX-R3: fail-closed real MainActivity synthetic-provider and release source gate."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANDROID = 'app/src/androidTest/java/com/sdvsync/ui/ux/NexR3NativeJourneyTest.kt'
RUNNER = 'scripts/devtool/nex_r3_emulator_ci.sh'
EVIDENCE = 'scripts/devtool/nex_r3_evidence.py'
WORKFLOW = '.github/workflows/nex-r3-real-native-journey.yml'
DOCUMENT = 'docs/devtool/NEX_R3_FINAL_ACCEPTANCE.md'
POLICY = 'docs/security/M3_RELEASE_POLICY.json'


def check(root: Path = ROOT) -> list[str]:
    root = Path(root)
    def read(name):
        file = root / name
        if not file.is_file() or file.is_symlink():
            raise ValueError('NEX_R3_MISSING_OR_SYMLINK:' + name)
        return file.read_text(encoding='utf-8')
    test = read(ANDROID)
    runner = read(RUNNER)
    evidence = read(EVIDENCE)
    ci = read(WORKFLOW)
    doc = read(DOCUMENT)
    nav = read('app/src/main/java/com/sdvsync/MainActivity.kt')
    browse = read('app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt')
    detail = read('app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt')
    file_review = read('app/src/main/java/com/sdvsync/ui/screens/ModDetailScreen.kt')
    provider = read('app/src/main/java/com/sdvsync/mods/api/NexusModSource.kt')
    policy = json.loads(read(POLICY))

    required = {
        'real activity and prelaunch injection': all(s in test for s in (
            'createAndroidComposeRule<MainActivity>()',
            'RuleChain.outerRule(methodName).around(fixture).around(compose)',
            'private val methodName = TestName()',
            'if (methodName.methodName != "noNexusKeyKeepsLocalModsRouteAvailable") {',
            'loadKoinModules(overrideModule)', 'unloadKoinModules(overrideModule)',
            'loadKoinModules(restoreModule)')),
        'synthetic-only credential and cleanup': all(s in test for s in (
            'NEX_R3_SYNTHETIC_NOT_A_REAL_NEXUS_KEY', 'getNexusApiKey()',
            'setNexusApiKey(FIXTURE_KEY)', 'setNexusApiKey(null)',
            'NEX_R3_REFUSED_NON_EPHEMERAL_DEVICE')),
        'no network fixture': all(s in test for s in (
            'class OfflineNexusTransport : Interceptor', 'url.host != "api.nexusmods.com"',
            'url.scheme != "https"', 'NEX_R3_REFUSED_UNEXPECTED_API_PATH',
            'NEX_R3_REFUSED_UNPINNED_GAME', 'modCategory', 'updatedAt')),
        'actual navigation and paging': all(s in test for s in (
            'realMainActivityDiscoverPagingDetailReviewAndBack',
            'cinderbox.screen.mods', 'cinderbox.mods.load-more', 'offsets.contains(50)',
            'cinderbox.screen.mod-detail', 'cinderbox.mod-detail.files',
            'Espresso.pressBack()', 'cinderbox.mod-detail.back')),
        'auth failures and no-key': all(s in test for s in (
            'Mode.AUTH_401', 'Mode.RATE_429', 'Mode.SERVER_503',
            'authRateLimitAndServiceFailuresStayReadOnly',
            'noNexusKeyKeepsLocalModsRouteAvailable', 'transport.paths.isEmpty()')),
        'no download evidence': all(s in test for s in (
            'assertNoDownloadRequests()', 'download_link', 'NEX_R3_REAL_NAVIGATION_SYNTHETIC_PROVIDER_PASS')),
        'offline hosted runner': all(s in runner for s in (
            'ro.kernel.qemu', 'ro.build.version.sdk', 'r48_offline_gate.py',
            'font_scale 1.0', 'NexR3NativeJourneyTest', 'OK (3 tests)',
            'nex_r3_evidence.py', 'exec-out run-as')),
        'source-and-PNG proof': all(s in evidence for s in (
            "'source_sha': source_sha", 'STAGES', 'DIMENSIONS', 'hashlib.sha256',
            'provider_responses_are_synthetic', 'live_nexus_schema_qualified_by_this_run')),
        'hosted workflow': all(s in ci for s in (
            'api-level: 36', 'assembleDebugAndroidTest', 'nex_r3_emulator_ci.sh',
            'nex_r3_gate.py', 'test_nex_r3_gate.py', 'if: always()',
            'android-emulator-runner@', ':app:testDebugUnitTest')),
        'test is honest': all(s in doc.lower() for s in (
            'synthetic', 'not a nexus', 'not release approval', '42446450123')),
        'production routes untouched': all(s in nav for s in (
            'onOpenRemoteMod = { modId, source ->',
            'navController.navigate("mod_detail_advanced/"',
            'ModDetailScreen(viewModel = viewModel')) and
            'RemoteModCard(mod = mod' in browse and
            'cinderbox.mod-detail.files' in detail and
            'fun ModDetailScreen(' in file_review and
            'getModFiles(modId: String)' in provider,
    }
    issues = ['NEX_R3_MISSING:' + name for name, found in required.items() if not found]
    for flag in ('release_enabled', 'publication_enabled',
                 'automatic_device_install', 'device_qualification_complete'):
        if policy.get(flag) is not False:
            issues.append('NEX_R3_RELEASE_POLICY_CHANGED:' + flag)
    for name, body in ((ANDROID, test), (RUNNER, runner), (EVIDENCE, evidence)):
        for unsafe in ('WebView(', 'installFile(', 'startDownload(', 'getDownloadUrl(',
                       'requestShizukuPermission(', 'Runtime.getRuntime('):
            if unsafe in body:
                issues.append('NEX_R3_UNSAFE_CODE:' + name + ':' + unsafe)
    if 'CINDERBOX_NEXUS_API_KEY' in ci + test + runner + evidence:
        issues.append('NEX_R3_LIVE_SECRET_REFERENCE_FORBIDDEN')
    if 'svc data disable' in runner:
        issues.append('NEX_R3_OBSOLETE_EMULATOR_CELLULAR_CMD')
    return issues


def main() -> int:
    try:
        issues = check()
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('NEX_R3_GATE_REFUSED:' + str(error))
        return 1
    if issues:
        print('\n'.join(issues))
        return 1
    print('NEX_R3_REAL_MAIN_ACTIVITY_SOURCE_CONTRACT_PASS_SYNTHETIC_NOT_LIVE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
