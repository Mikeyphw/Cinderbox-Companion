#!/usr/bin/env python3
"""Bounded, fail-closed API36 SDK package recovery for hosted Android emulator CI.

Executes only known SDK packages; no app data, network tokens, or secrets are read.
Never substitutes a different API, ABI, image provider or fake success receipt.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

PREFIX = 'CBNX04D_SDK'
PACKAGES = (
    ('platforms;android-35', 'platforms/android-35/android.jar'),
    ('platforms;android-36', 'platforms/android-36/android.jar'),
    ('build-tools;35.0.0', 'build-tools/35.0.0/aapt'),
    ('system-images;android-36;google_apis;x86_64',
     'system-images/android-36/google_apis/x86_64/system.img'),
)
MAX_ATTEMPTS = 3
ATTEMPT_TIMEOUT_SECONDS = 360
BACKOFF_SECONDS = (0, 2, 5)


def sdk_root():
    first = os.environ.get('ANDROID_HOME', '')
    second = os.environ.get('ANDROID_SDK_ROOT', '')
    if not first or not os.path.isabs(first) or not os.path.isdir(first):
        raise RuntimeError('ANDROID_HOME_MISSING')
    if second and os.path.realpath(second) != os.path.realpath(first):
        raise RuntimeError('ANDROID_SDK_ROOT_MISMATCH')
    root = Path(first)
    if root.is_symlink():
        raise RuntimeError('ANDROID_SDK_SYMLINK')
    return root


def installed(root: Path, rel: str):
    parts = Path(rel).parts
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeError('UNSAFE_SDK_PACKAGE_LINK')
    return current.is_file() and current.stat().st_size > 0


def main():
    root = sdk_root()
    command = shutil.which('sdkmanager')
    if not command:
        raise RuntimeError('SDKMANAGER_NOT_FOUND')
    for package, marker in PACKAGES:
        success = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1 and os.environ.get('CBNX04D_SDK_TEST_FAST') != '1':
                time.sleep(BACKOFF_SECONDS[attempt - 1])
            print(f'{PREFIX}_ATTEMPT package={package} try={attempt}/{MAX_ATTEMPTS}', flush=True)
            try:
                result = subprocess.run([command, '--install', package],
                    check=False, timeout=ATTEMPT_TIMEOUT_SECONDS)
                rc = result.returncode
            except subprocess.TimeoutExpired:
                rc = 124
            if rc == 0 and installed(root, marker):
                # The emulator must have its package metadata, not merely a partial image.
                if package.startswith('system-images;'):
                    metadir = Path(marker).parent
                    if not (installed(root, str(metadir / 'source.properties')) and
                            installed(root, str(metadir / 'package.xml'))):
                        print(f'{PREFIX}_INCOMPLETE_PACKAGE package={package}', flush=True)
                        continue
                success = True
                print(f'{PREFIX}_PACKAGE_VERIFIED package={package}', flush=True)
                break
            print(f'{PREFIX}_RETRYABLE_FAILURE package={package} rc={rc}', flush=True)
        if not success:
            raise RuntimeError('PACKAGE_INSTALL_UNQUALIFIED:' + package)
    print(PREFIX + '_EXACT_API36_GOOGLE_APIS_X86_64_READY', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as exc:
        print(PREFIX + '_REFUSED:' + str(exc), file=sys.stderr, flush=True)
        sys.exit(1)
