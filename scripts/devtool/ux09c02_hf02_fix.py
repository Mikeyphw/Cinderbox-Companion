#!/usr/bin/env python3
"""UX09C02 HF02 exact-Git-source-locked M4 and LazyColumn test repair.

No runtime or privileged code changes; only offline regression and Android UI tests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PINNED_COMMIT = '4776890ccb7356d4f7848d35c71cb9c395142ac0'
PINNED_TREE = 'd93baab00edf6902c7b61755a232cdc26b318ba1'
ANDROID_TEST = 'app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt'
M4_TEST = 'scripts/devtool/test_m4_local_first.py'
PREIMAGES = {
    ANDROID_TEST: '960117d675e6fc228312fb5f852b1c06f29c900c',
    M4_TEST: 'a4fc389938955e6e4f780e09e8323c9355129d4f',
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def once(data: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = data.count(old)
    assert count == 1, f'UX09C02_HF02_ANCHOR_COUNT:{label}:{count}'
    assert old != new, f'UX09C02_HF02_NOOP:{label}'
    return data.replace(old, new, 1)


def patch_android(data: bytes) -> bytes:
    data = once(
        data,
        b'import androidx.compose.ui.test.performScrollTo\n',
        b'import androidx.compose.ui.test.hasTestTag\n'
        b'import androidx.compose.ui.test.performScrollToNode\n',
        'android-imports',
    )
    data = once(
        data,
        b'        rule.onNodeWithTag("cinderbox.mods.advanced").performScrollTo().performClick()\n',
        b'        // The Advanced action belongs to a LazyColumn item. Scroll the container\n'
        b'        // to that item before clicking: a child-level scroll action is unsupported.\n'
        b'        rule.onNodeWithTag("cinderbox.screen.mods")\n'
        b'            .performScrollToNode(hasTestTag("cinderbox.mods.advanced"))\n'
        b'        rule.onNodeWithTag("cinderbox.mods.advanced").performClick()\n',
        'lazy-column-navigation',
    )
    assert b'performScrollTo()' not in data, 'UX09C02_HF02_BAD_SCROLL_ACTION'
    assert b'performScrollToNode(hasTestTag("cinderbox.mods.advanced"))' in data
    return data


def patch_m4(data: bytes) -> bytes:
    data = once(
        data,
        b"        assert 'Continue offline' in login\n"
        b"        assert 'onContinueOffline' in login\n"
        b"        assert 'navController.navigate(\"main\")' in nav\n",
        b"        # UX-09C02: local mode is already active; Login is only an optional Steam flow.\n"
        b"        # The return action is explicit, and its callback still routes to the app.\n"
        b"        assert 'Continue offline' not in login\n"
        b"        assert 'CinderboxSteamLoginHeader(onBack = onContinueOffline)' in login\n"
        b"        assert 'onContinueOffline = {' in nav\n"
        b"        assert 'if (!navController.popBackStack()) navController.navigate(\"main\")' in nav\n"
        b"        assert 'onOpenSettings = { navController.navigate(\"prelogin_settings\") }' in nav\n",
        'm4-offline-navigation',
    )
    assert b'Continue offline\' in login' not in data
    return data


def patches(root: Path) -> dict[str, bytes]:
    assert git(root, 'rev-parse', 'HEAD') == PINNED_COMMIT, 'UX09C02_HF02_HEAD_DRIFT'
    assert git(root, 'rev-parse', 'HEAD^{tree}') == PINNED_TREE, 'UX09C02_HF02_TREE_DRIFT'
    out = {}
    for name, expected_blob in PREIMAGES.items():
        path = root / name
        assert path.is_file() and not path.is_symlink(), 'UX09C02_HF02_MISSING_SOURCE:'+name
        assert git(root, 'hash-object', name) == expected_blob, 'UX09C02_HF02_PREIMAGE_DRIFT:'+name
        old = path.read_bytes()
        new = patch_android(old) if name == ANDROID_TEST else patch_m4(old)
        assert old != new
        out[name] = new
    return out


def apply(root: Path, replacements: dict[str, bytes]) -> None:
    originals = {name: (root / name).read_bytes() for name in replacements}
    try:
        for name, value in replacements.items():
            (root / name).write_bytes(value)
        for name, value in replacements.items():
            assert (root / name).read_bytes() == value, 'UX09C02_HF02_POSTIMAGE_DRIFT:'+name
    except BaseException:
        for name, original in originals.items():
            (root / name).write_bytes(original)
        raise


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    root = args.repo.resolve()
    changes = patches(root)
    if args.apply:
        apply(root, changes)
    print(json.dumps({'result': 'UX09C02_HF02_M4_AND_LAZY_SCROLL_REPAIRS_PASS',
                      'applied': args.apply, 'paths': sorted(changes),
                      'post_sha256': {k: hashlib.sha256(v).hexdigest()
                                      for k, v in changes.items()}}, sort_keys=True))


if __name__ == '__main__':
    main()
