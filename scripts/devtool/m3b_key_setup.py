#!/usr/bin/env python3
"""Explicit local key bootstrap. Never commits, prints or uploads key material.

Call only when the user has decided on a stable release signing identity.
Store and key passwords are entered interactively by keytool, not as argv.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['create', 'inspect'])
    p.add_argument('--keystore', type=Path, default=Path.home() / '.config/cinderbox-signing/release.jks')
    args = p.parse_args()
    path = args.keystore.expanduser().absolute()
    keytool = shutil.which('keytool')
    if not keytool:
        print('keytool (JDK 17+) is required', file=sys.stderr)
        return 1
    if path.is_symlink() or path.parent.is_symlink():
        print('Refusing symlinked keystore paths', file=sys.stderr)
        return 1
    try:
        if args.command == 'create':
            if not sys.stdin.isatty():
                raise ValueError('Key creation requires an interactive terminal')
            if path.exists():
                raise ValueError('Keystore already exists; never overwrite a signing identity')
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(path.parent, stat.S_IRWXU)
            print('Generating a new, long-lived signing key. Back it up securely before use.')
            result = subprocess.run([
                keytool, '-genkeypair', '-storetype', 'PKCS12', '-keystore', str(path),
                '-alias', 'cinderbox', '-keyalg', 'RSA', '-keysize', '3072',
                '-validity', '10950', '-dname', 'CN=Cinderbox Companion, O=Independent, C=BR',
            ], timeout=240, check=False)
            if result.returncode != 0 or not path.is_file():
                raise ValueError('Key generation failed; check for an incomplete keystore before retrying')
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            print('Keystore created outside the repository:', path)
            print('Use inspect to obtain the public certificate fingerprint.')
            return 0
        if not path.is_file():
            raise ValueError('Keystore not found')
        print('The next command may request the keystore password. Never paste it into chat.')
        result = subprocess.run([keytool, '-list', '-v', '-keystore', str(path), '-alias', 'cinderbox'],
                                timeout=90, check=False)
        return 0 if result.returncode == 0 else 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f'M3B KEY SETUP: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
