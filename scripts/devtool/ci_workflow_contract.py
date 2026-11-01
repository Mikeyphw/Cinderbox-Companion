#!/usr/bin/env python3
"""Fail-closed, source-bound resolution of Cinderbox's A10 reusable legacy CI.

Reading `devtool-android-build.yml` for legacy regression coverage now requires
following its *exact* authorized, repository-local reusable workflow call into
`build.yml`. Only the reusable legacy branch is projected; its scope is NOT a
claim that the separate native A07 lane executes every M3-M24 test.

Used by existing source gates that previously assumed the old legacy steps were
copied into both YAMLs. All provenance hashes still cover original raw files.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

LEGACY = '.github/workflows/build.yml'
DISPATCH = '.github/workflows/devtool-android-build.yml'
FROZEN_STANDARD_CI_SHA256 = 'ddd3c35fb54fbb12b5de9d17b2a83d09a1059562de40030334bee5dc51cb4742'
A10_INSERT_START = '      # A10: keep the original Devtool legacy artifact contract only when'
A10_INSERT_END = '      - name: M23 synthetic Android test source contract\n'


def _raw(root: Path, relative: str) -> str:
    if Path(relative).is_absolute() or '..' in Path(relative).parts or '\\' in relative:
        raise ValueError('A10_INVALID_SOURCE_PATH')
    current = Path(root)
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('A10_SYMLINK_SOURCE')
    if not current.is_file():
        raise ValueError('A10_SOURCE_MISSING: ' + relative)
    return current.read_text('utf8')


def validated_legacy_and_dispatch(root: Path) -> tuple[str, str]:
    legacy = _raw(root, LEGACY)
    manual = _raw(root, DISPATCH)
    required = ("  build-debug-apk:\n"
                "    if: ${{ inputs.a05_mode != 'native-only' }}\n"
                "    uses: ./.github/workflows/build.yml\n"
                "    permissions:\n"
                "      contents: read\n"
                "    secrets: inherit\n")
    if manual.count(required) != 1 or manual.count('uses: ./.github/workflows/build.yml') != 1:
        raise ValueError('A10_DELEGATED_LEGACY_JOB_DRIFT')
    if ('  workflow_call:\n' not in legacy or '  push:\n' not in legacy or
            '  pull_request:\n' not in legacy):
        raise ValueError('A10_LEGACY_TRIGGERS_DRIFT')
    if legacy.count(A10_INSERT_START) != 1 or legacy.count(A10_INSERT_END) != 1:
        raise ValueError('A10_LEGACY_FALLBACK_ARTIFACT_MISSING')
    standard = legacy.replace('  workflow_call:\n', '', 1)
    start = standard.index(A10_INSERT_START)
    end = standard.index(A10_INSERT_END)
    if start >= end:
        raise ValueError('A10_FALLBACK_STAGE_ORDER')
    standard = standard[:start] + standard[end:]
    if hashlib.sha256(standard.encode()).hexdigest() != FROZEN_STANDARD_CI_SHA256:
        raise ValueError('A10_CANONICAL_LEGACY_CI_DRIFT')
    fallback = legacy.split(A10_INSERT_START, 1)[1].split(A10_INSERT_END, 1)[0]
    for token in ("if: github.event_name == 'workflow_dispatch'", 'sha256sum debug.apk > SHA256SUMS',
                  'BUILD_INFO.txt', 'M3_PROVENANCE.json', 'M13_QUALIFICATION.json',
                  'name: devtool-android-debug-apk'):
        if token not in fallback:
            raise ValueError('A10_LEGACY_ARTIFACT_SHAPE_DRIFT')
    if ("default: 'native-only'" not in manual or 'default: true' not in manual or
            '  a07-native-debug-build:' not in manual or
            'invoke --target cinderbox build' not in manual):
        raise ValueError('A10_NATIVE_DEFAULT_OR_DAG_DRIFT')
    return legacy, manual


def effective_ci_source(root: Path, relative: str) -> str:
    """Return raw source for other paths, exact native+delegated fallback for A10 dispatch.

    Do not use this merged view for hashing a tracked file or certifying that
    *A07 native* executes the delegated test suite.
    """
    if relative != DISPATCH:
        return _raw(root, relative)
    legacy, manual = validated_legacy_and_dispatch(root)
    return manual + '\n# A10 exact local reusable legacy CI source follows\n' + legacy
