#!/usr/bin/env python3
"""UX09C02 HF01, exact-Git-blob guarded two-file repair. No Gradle or privileged writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PINNED_COMMIT = '526e9cbdf672e7bb2904320dd93f9af1f4998552'
PINNED_TREE = '7d3726f1cc2dcabe93bf686b9c07f22365eefcb7'
PATCHES = {
    'app/src/androidTest/java/com/sdvsync/ui/ux/UxDeviceChromeTest.kt': (
        'dc8ac03ffcd72d3012f9edb06627b2d090e6e5d7',
        b'import androidx.compose.ui.test.assertExists\n', b'',
    ),
    'app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt': (
        'd542f236dfa962ee5aa1d839582e4cbbb1ee46fa',
        b'Text("Connection settings")',
        b'Text(stringResource(R.string.settings_title))',
    ),
}

def run_git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

def replace_unique(data: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = data.count(old)
    assert count == 1, f'UX09C02_HF01_ANCHOR_COUNT:{label}:{count}'
    updated = data.replace(old, new, 1)
    assert updated != data, f'UX09C02_HF01_NO_CHANGE:{label}'
    return updated

def validate_preimages(root: Path) -> dict[str, bytes]:
    assert run_git(root, 'rev-parse', 'HEAD') == PINNED_COMMIT, 'UX09C02_HF01_HEAD_DRIFT'
    assert run_git(root, 'rev-parse', 'HEAD^{tree}') == PINNED_TREE, 'UX09C02_HF01_TREE_DRIFT'
    patches: dict[str, bytes] = {}
    for name, (expected_blob, before, after) in PATCHES.items():
        path = root / name
        assert path.is_file() and not path.is_symlink(), f'UX09C02_HF01_MISSING_SOURCE:{name}'
        assert run_git(root, 'hash-object', name) == expected_blob, f'UX09C02_HF01_PREIMAGE_DRIFT:{name}'
        patches[name] = replace_unique(path.read_bytes(), before, after, name)
    assert b'Continue offline' not in patches['app/src/main/java/com/sdvsync/ui/screens/LoginScreen.kt'], 'UX09C02_HF01_OFFLINE_BUTTON_REGRESSION'
    return patches

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.repo.resolve()
    patches = validate_preimages(root)
    if args.apply:
        originals = {name:(root/name).read_bytes() for name in patches}
        try:
            for name, data in patches.items():
                (root/name).write_bytes(data)
            for name, data in patches.items():
                assert (root/name).read_bytes() == data, f'UX09C02_HF01_POSTIMAGE_MISMATCH:{name}'
        except BaseException:
            for name, data in originals.items():
                (root/name).write_bytes(data)
            raise
    print(json.dumps({'result':'UX09C02_HF01_TWO_COMPILER_AND_M3_REPAIRS_PASS',
                      'applied': args.apply, 'paths': sorted(patches),
                      'post_sha256': {k:hashlib.sha256(v).hexdigest() for k,v in patches.items()}}, sort_keys=True))

if __name__ == '__main__':
    main()
