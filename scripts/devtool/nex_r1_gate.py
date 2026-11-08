#!/usr/bin/env python3
"""Native Nexus catalog source qualification. No device, network or Gradle required."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]

def source(path,root=ROOT):
    f=root/path
    assert f.is_file() and not f.is_symlink(), f'NEX_R1_MISSING_OR_SYMLINK:{path}'
    return f.read_text(encoding='utf8')

def check(root=ROOT):
    root=Path(root)
    base='app/src/main/java/com/sdvsync/'
    operation=source(base+'mods/api/NexusCatalogOperation.kt',root)
    filters=source(base+'mods/api/NexusCatalogFilters.kt',root)
    legacy=source(base+'mods/api/NexusSearchOperation.kt',root)
    provider=source(base+'mods/api/NexusModSource.kt',root)
    vm=source(base+'ui/viewmodels/ModBrowseViewModel.kt',root)
    ui=source(base+'ui/screens/ApprovedModsScreen.kt',root)
    for item in ('gameId','1303','NEXUS_SEARCH_PAGE_SIZE','categoryName','includeTag','excludeTag',
                 'updatedAt','downloads','endorsements','WILDCARD','NOT_EQUALS',
                 'GT','NexusSearchOperation','sort: [ModsSort!]','offset'):
        assert item in operation,f'NEX_R1_GRAPHQL_FILTER_MISSING:{item}'
    assert '"filter" to mapOf("filter" to clauses, "op" to "AND")' in operation
    assert '"sort" to listOf(' in operation
    assert 'fun createNexusSearchOperation(' in legacy,'NEX_R1_LEGACY_SEARCH_REMOVED'
    assert 'fun createNexusCatalogOperation(' in operation
    assert 'suspend fun browse(' in provider and 'createNexusCatalogOperation(normalizedQuery, filters, page)' in provider
    assert 'val operation = createNexusSearchOperation(normalizedQuery, page)' not in provider
    assert 'val filters: NexusCatalogFilters' in vm
    assert 'val totalResults: Int = 0' in vm
    assert 'nexusSource.browse(normalized, filters = filters, page = 1)' in vm
    assert 'filters = current.filters, page = nextPage' in vm
    assert 'mergeSearchPages(it.mods, result.mods)' in vm
    assert 'requestGate.next()' in vm and 'updateIfCurrent(generation)' in vm
    for item in ('nex.r1.filter.sheet','nex.r1.filter.apply','nex.r1.filter.category',
                 'nex.r1.filter.exclude-tag','browseViewModel.applyFilters(',
                 'browse.totalResults','NexusCatalogSort.entries','Clear provider filters'):
        assert item in ui,f'NEX_R1_UI_FILTER_MISSING:{item}'
    assert 'categoryName == mod.categoryName' not in ui,'NEX_R1_LOCAL_CATEGORY_FILTER_NOT_REMOVED'
    assert 'DiscoverSort' not in ui,'NEX_R1_LOCAL_SORT_NOT_REMOVED'
    assert 'WebView(' not in ui and 'ChromeXt' not in ui,'NEX_R1_WEBVIEW_FORBIDDEN'
    for forbidden in ('startDownload(', 'installMod(', 'toggleMod(', 'applyProfile(',
                      'deleteRecursively(', 'requestShizukuPermission('):
        assert forbidden not in ui,f'NEX_R1_UNSAFE_OPERATION_IN_BROWSE:{forbidden}'
    assert 'cinderbox.screen.mods' in ui and 'cinderbox.mods.advanced' in ui
    assert 'CinderboxDarkTokens' in ui and 'NexusCatalogFilters' in filters
    policy=json.loads(source('docs/security/M3_RELEASE_POLICY.json',root))
    for flag in ('release_enabled','publication_enabled','automatic_device_install','device_qualification_complete'):
        assert policy[flag] is False,f'NEX_R1_RELEASE_GATE_CHANGED:{flag}'
    return {'result':'NEX_R1_NATIVE_CATALOG_SOURCE_PASS','graphql_variables':True,
            'server_filter_and_sort':True,'page_count':50,'real_ui_required':True,
            'download_changes':False,'webview':False,'physical_device_qualified':False,
            'native_goldens_approved':False}

if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
