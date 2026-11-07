#!/usr/bin/env python3
"""Exact-preimage production UI-only patch for UX09D01 REPLACEMENT.

Five existing files are verified before any writes. All other changes use Devtool's
canonical add-only overlay. No Android/Gradle execution in Termux.
"""
from __future__ import annotations
import argparse
import pathlib
import subprocess

BASE = 'b9e7883e04431d49f12dda9337d2922f59c0e475'
PREIMAGES = {
    'app/src/main/java/com/sdvsync/MainActivity.kt': 'a4a536514ee59f436f01ba92a02514227203837a',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt': 'f9806a74ea79a48a780d6b22d9c7edc99ac712f6',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt': '45ea27fb77f2bfe10b0b23b2568bd93c5a84a2dd',
    'app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt': 'd2d1f6aa7038c56ac4ab0ddb76b0c43de1fc4c8b',
    'app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt': '9357b366a91e5f069c2110a7a8b30ce12ac6811f',
}


def replace_once(source: str, before: str, after: str, label: str) -> str:
    count = source.count(before)
    if count != 1:
        raise AssertionError(f'UX09D01_PREIMAGE_MISMATCH:{label}:count={count}')
    return source.replace(before, after, 1)


def patches():
    main = 'app/src/main/java/com/sdvsync/MainActivity.kt'
    mods = 'app/src/main/java/com/sdvsync/ui/screens/ApprovedModsScreen.kt'
    saves = 'app/src/main/java/com/sdvsync/ui/screens/ApprovedSavesScreen.kt'
    more = 'app/src/main/java/com/sdvsync/ui/screens/ApprovedMoreScreen.kt'
    operations = 'app/src/main/java/com/sdvsync/ui/screens/OperationCenterScreen.kt'
    return {
        main: [
            # Android API 36 edge-to-edge MUST keep light status text on fixed dark UI.
            ('        enableEdgeToEdge()\n',
             '        enableEdgeToEdge(statusBarStyle = androidx.activity.SystemBarStyle.dark(android.graphics.Color.TRANSPARENT))\n'),
            ('                    onOpenSyncHistory = { parentNavController.navigate("sync_log") },\n',
             '                    onOpenSyncHistory = { parentNavController.navigate("sync_log") },\n'
             '                    onOpenOperationCenter = { parentNavController.navigate("operation_center") },\n'),
            ('                    onOpenQueue = { parentNavController.navigate("download_queue") },\n',
             '                    onOpenQueue = { parentNavController.navigate("download_queue") },\n'
             '                    onOpenOperationCenter = { parentNavController.navigate("operation_center") },\n'),
        ],
        mods: [
            ('import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark\n',
             'import com.sdvsync.ui.components.CinderboxBrandTopBar\n'
             'import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark\n'),
            ('    browseViewModel: ModBrowseViewModel = koinViewModel()\n',
             '    browseViewModel: ModBrowseViewModel = koinViewModel(),\n'
             '    onOpenOperationCenter: () -> Unit = {}\n'),
            ('        item {\n            Column {\n                Text("MAKE IT YOUR VALLEY",',
             '        item {\n'
             '            CinderboxBrandTopBar(\n'
             '                subtitle = "YOUR MOD LIBRARY",\n'
             '                onOpenOperationCenter = onOpenOperationCenter\n'
             '            )\n'
             '        }\n'
             '        item {\n            Column {\n                Text("MAKE IT YOUR VALLEY",'),
            ('                Text("Your mods", color = Dark.Ink,\n',
             '                Text("Mods", color = Dark.Ink,\n'),
            ('        item { ModsPaneSelector(pane) { pane = it } }\n',
             '        item { ModsPaneSelector(pane) { pane = it } }\n'
             '        // Always-visible entry point, independent of Nexus listings or category.\n'
             '        item {\n'
             '            OutlinedButton(\n'
             '                onClick = onOpenAdvancedMods,\n'
             '                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)\n'
             '                    .testTag("cinderbox.mods.advanced"),\n'
             '                shape = RoundedCornerShape(12.dp)\n'
             '            ) { Text("Manage local mods") }\n'
             '        }\n'),
            ('        item {\n'
             '            ModsPanel("Advanced mod management",\n'
             '                "Open the existing manager for imports, profile previews and explicitly reviewed changes.") {\n'
             '                OutlinedButton(onClick = onOpenAdvancedMods,\n'
             '                    modifier = Modifier.fillMaxWidth().testTag("cinderbox.mods.advanced")) {\n'
             '                    Text("Open advanced manager")\n'
             '                }\n'
             '            }\n'
             '        }\n', ''),
        ],
        saves: [
            ('import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark\n',
             'import com.sdvsync.ui.components.CinderboxBrandTopBar\n'
             'import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark\n'),
            ('    viewModel: DashboardViewModel = koinViewModel()\n',
             '    viewModel: DashboardViewModel = koinViewModel(),\n'
             '    onOpenOperationCenter: () -> Unit = {}\n'),
            ('        item {\n            Column {\n                Text("THE STORIES YOU\'VE GROWN",',
             '        item {\n'
             '            CinderboxBrandTopBar(\n'
             '                subtitle = "LOCAL & CLOUD",\n'
             '                onOpenOperationCenter = onOpenOperationCenter\n'
             '            )\n'
             '        }\n'
             '        item {\n            Column {\n                Text("THE STORIES YOU\'VE GROWN",'),
        ],
        operations: [
            ('import androidx.compose.ui.platform.LocalContext\n',
             'import androidx.compose.ui.platform.LocalContext\n'
             'import androidx.compose.ui.platform.testTag\n'),
            ('    Scaffold(topBar = { StardewTopAppBar("Operation center", navigationIcon = {\n',
             '    Scaffold(modifier = Modifier.testTag("cinderbox.screen.operation-center"),\n'
             '        topBar = { StardewTopAppBar("Operation center", navigationIcon = {\n'),
            ('        TextButton(onClick = onBack) { Text("Back") }\n',
             '        TextButton(onClick = onBack,\n'
             '            modifier = Modifier.testTag("cinderbox.operation-center.back")) { Text("Back") }\n'),
        ],
        more: [
            ('import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark\n',
             'import com.sdvsync.ui.components.CinderboxBrandTopBar\n'
             'import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark\n'),
            ('        verticalArrangement = Arrangement.spacedBy(12.dp)) {\n'
             '        Row(verticalAlignment = Alignment.CenterVertically,',
             '        verticalArrangement = Arrangement.spacedBy(12.dp)) {\n'
             '        CinderboxBrandTopBar(\n'
             '            subtitle = "SETTINGS & MORE",\n'
             '            onOpenOperationCenter = onOpenOperationCenter\n'
             '        )\n'
             '        Row(verticalAlignment = Alignment.CenterVertically,'),
        ],
    }


def patch_source(path: str, content: str) -> str:
    if 'CinderboxBrandTopBar(' in content or 'import com.sdvsync.ui.components.CinderboxBrandTopBar' in content:
        raise AssertionError('UX09D01_PREIMAGE_MISMATCH:ALREADY_PATCHED:'+path)
    if path not in patches():
        raise AssertionError('UX09D01_UNEXPECTED_SOURCE:'+path)
    updated = content
    for n,(before,after) in enumerate(patches()[path]):
        updated = replace_once(updated, before, after, f'{path}:anchor-{n}')
    if updated == content: raise AssertionError('UX09D01_NO_CHANGE:'+path)
    return updated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path('.'))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--apply', action='store_true')
    action.add_argument('--source-check', action='store_true')
    args = parser.parse_args()
    root = args.repo.resolve()
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
    assert head == BASE, f'UX09D01_REFUSED_WRONG_HEAD:{head}'
    updated = {}
    # Validate all source preimages BEFORE writing any file.
    for rel,expected in PREIMAGES.items():
        file = root / rel
        if not file.is_file() or file.is_symlink():
            raise AssertionError('UX09D01_SOURCE_NOT_FILE:'+rel)
        blob = subprocess.check_output(['git','hash-object','--',str(file)], cwd=root, text=True).strip()
        if blob != expected: raise AssertionError(f'UX09D01_SOURCE_DRIFT:{rel}:{blob}')
        updated[rel] = patch_source(rel, file.read_text(encoding='utf-8'))
    if args.apply:
        for rel,text in updated.items(): (root/rel).write_text(text, encoding='utf-8')
    print('UX09D01_FIVE_EXACT_SOURCE_PREIMAGES_PASS' if not args.apply else 'UX09D01_NORMAL_UI_SOURCE_PATCH_APPLIED')

if __name__ == '__main__': main()
