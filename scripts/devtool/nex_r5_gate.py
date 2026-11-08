#!/usr/bin/env python3
"""NEX-R5 source-only regression gate. Hosted runtime proof is separate."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DETAIL='app/src/main/java/com/sdvsync/ui/screens/ApprovedModDetailScreen.kt'
HTML='app/src/main/java/com/sdvsync/ui/components/HtmlText.kt'
LEGACY='app/src/main/java/com/sdvsync/ui/screens/ModDetailScreen.kt'
VIEWMODEL='app/src/main/java/com/sdvsync/ui/viewmodels/ModDetailViewModel.kt'
LINKS='app/src/main/java/com/sdvsync/mods/api/NexusModPageLinks.kt'
TEST='app/src/androidTest/java/com/sdvsync/ui/ux/NexR5UnifiedDetailTest.kt'
RUNNER='scripts/devtool/nex_r5_emulator_ci.sh'
CI='.github/workflows/nex-r5-unified-details.yml'
POLICY='docs/security/M3_RELEASE_POLICY.json'
PROBE='scripts/devtool/nex_r5_community_probe.py'
PROBE_TEST='scripts/devtool/test_nex_r5_community_probe.py'
SCHEMA_DOC='scripts/devtool/fixtures/nex_r5_community/documented_v2_schema.json'
SCHEMA_FUTURE='scripts/devtool/fixtures/nex_r5_community/hypothetical_mod_scoped_schema.json'


def check(root: Path=ROOT)->list[str]:
    def read(rel):
        p=root/rel
        if p.is_symlink() or not p.is_file():raise ValueError('NEX_R5_MISSING:'+rel)
        return p.read_text()
    detail,html,legacy,viewmodel,links,test,runner,ci=(read(f) for f in
        (DETAIL,HTML,LEGACY,VIEWMODEL,LINKS,TEST,RUNNER,CI))
    probe,probe_test,fixture,future=(read(x) for x in (PROBE,PROBE_TEST,SCHEMA_DOC,SCHEMA_FUTURE))
    policy=json.loads(read(POLICY))
    required={
        'same approved details route':all(s in detail for s in (
            'cinderbox.screen.mod-detail','NexR2Display.groupedFiles(files)',
            'cinderbox.mod-detail.files','onReviewFiles','Compatibility not verified')),
        'formatted description':all(s in detail for s in (
            'RichNexusDescription(description', 'toHtmlIfFormatted(bounded)',
            'HtmlText(html = formatted', 'nex.r2.detail.description')),
        'download-for-review':all(s in detail for s in (
            'onDownloadForReview = viewModel::installFile',
            'onDownloadForReview(file.fileId)', 'nex.r5.download-for-review',
            'Download for review', 'REVIEW_REQUIRED','never silently installs',
            'requestInFlight = state.isDownloading', 'val busy = requestInFlight ||')),
        'single-flight URL fetch':all(s in viewmodel for s in (
            'downloadLinkRequest.compareAndSet(false, true)',
            'isDownloading = true', 'isDownloading = false',
            'downloadLinkRequest.set(false)',
            'catch (cancelled: CancellationException)',
            'downloadManager.startDownload(url, modName, modId, source)')),
        'community browser fallback':all(s in detail for s in (
            'NexusModPageLinks.forTab(mod.modId, "posts")',
            'NexusModPageLinks.forTab(mod.modId, "images")',
            'NexusModPageLinks.forTab(mod.modId, "videos")',
            'nex.r5.open-posts', 'nex.r5.images', 'not exposed by a verified API contract')),
        'nonduplicate legacy file route':all(s in legacy for s in (
            'title = "Files & downloads"','File download options',
            'Download for review','fun ModDetailScreen(')) and
            '// Header card' not in legacy and '// Description card' not in legacy,
        'safe description rendering':all(s in html for s in (
            'safeNexusSpanned','unsafeBlocks','unsafeElements',
            'getSpans(0, result.length, URLSpan::class.java)',
            'NexusModPageLinks.safeExternalHttps(span.url)',
            'tv.text = safeNexusSpanned(html)')),
        'safe browser links':all(s in links for s in (
            'positiveModId','allowedTabs','safeExternalHttps',
            'uri.userInfo != null','uri.port != -1',
            'host.endsWith(".local")')),
        'synthetic hosted tests':all(s in test for s in (
            'createComposeRule()', 'safeNexusSpanned(', 'oneNativeOverviewShowsFormattedTextFilesAndExternalCommunity',
            'formattedHtmlRemovesExecutableMarkupAndUnsafeUrlSpans',
            'requestInFlightDisablesDuplicateDownloadTap','nex.r5.download-for-review',
            'nex.r5.open-posts', 'capture("community")')),
        'community-schema-probe':all(s in probe for s in (
            'SCHEMA_QUERY', 'IDENTITY_QUERY', 'assess_schema(', 'probe_live(',
            'native_qualified', 'NO_VERIFIED_MOD_RELATION',
            'GRAPHQL_ERRORS', '429', 'NoRedirect', 'MAX_HTTP_BYTES',
            'personal_or_media_content_fetched', 'credential_logged')),
        'community-probe-hardened-tests':all(s in probe_test for s in (
            'test_thread_id_is_not_mod_id',
            'test_current_documented_graphql_is_not_mod_scoped',
            'test_future_schema_is_candidate_only_not_native_proof',
            'test_no_live_requests_for_offline_fixture',
            'test_atomic_no_overwrite_or_symlink')),
        'community-documentation-fixtures':all(s in fixture+future for s in (
            'mod', 'mediaFilter', 'commentThread')),
        'community-hosted-observability':all(s in ci for s in (
            'community-schema-probe', 'nex_r5_community_probe.py',
            'nex-r5-community-schema-receipt', 'test_nex_r5_community_probe.py')),
        'hosted API36':all(s in runner+ci for s in (
            'ro.kernel.qemu','r48_offline_gate.py','font_scale 1.0',
            'NexR5UnifiedDetailTest','api-level: 36',
            ':app:assembleDebugAndroidTest','nex_r5_evidence.py')),
    }
    errors=['NEX_R5_MISSING:'+k for k,ok in required.items() if not ok]
    for f in ('release_enabled','publication_enabled','automatic_device_install',
              'device_qualification_complete'):
        if policy.get(f) is not False:errors.append('NEX_R5_RELEASE_GUARD:'+f)
    for token in ('WebView(', 'requestShizukuPermission(', 'installPackage(',
                  'startDownload(', 'getDownloadUrl(', 'Runtime.getRuntime('):
        if token in detail+html+links+test:errors.append('NEX_R5_UNSAFE:'+token)
    return errors


if __name__=='__main__':
    try:issues=check()
    except (ValueError,OSError,TypeError,KeyError) as e:raise SystemExit('NEX_R5_REFUSED:'+str(e))
    if issues:raise SystemExit('\n'.join(issues))
    print('NEX_R5_SOURCE_GATE_PASS_HOSTED_ANDROID_PENDING')
