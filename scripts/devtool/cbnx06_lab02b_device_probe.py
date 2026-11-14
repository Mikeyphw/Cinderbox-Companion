#!/usr/bin/env python3
"""CB-NX06 LAB02B: strictly read-only Android package / hosted-APK identity probe.

Never installs, uninstalls, starts activities, requests permissions, invokes su,
reads personal game content, or performs network requests. Only OS package
metadata, getprop, and APK hashes are inspected. This alone is NOT live Nexus,
file-system immutability, rollback, or release qualification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

LAB='com.sdvsync.cbnx06lab'
PROD='com.sdvsync'
class Refused(Exception): pass

def require(ok, reason):
    if not ok: raise Refused(reason)

def sha256_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def command(argv):
    try: r=subprocess.run(argv,check=False,capture_output=True,text=True,timeout=25)
    except (OSError,subprocess.TimeoutExpired) as exc:raise Refused('DEVICE_COMMAND_UNAVAILABLE') from exc
    require(r.returncode==0,'DEVICE_READ_ONLY_COMMAND_FAILED')
    return r.stdout.strip()

def adb(serial, *args):return command(['adb','-s',serial,*args])

def apk_path(serial,package):
    out=adb(serial,'shell','pm','path',package)
    lines=out.splitlines()
    if not lines:return None
    # Ignore split APK setups: the hosted artifact is a single universal APK.
    require(len(lines)==1 and lines[0].startswith('package:'),'INSTALLED_APK_NOT_SINGLE')
    path=lines[0][len('package:'):].strip()
    require(path.startswith('/data/app/') and path.endswith('/base.apk') and
            '\n' not in path and '\r' not in path and '\x00' not in path and
            not any(x in path for x in ('..','\\','\"',"'",' ')) and
            re.fullmatch(r'/data/app/[A-Za-z0-9_+./~=-]+',path) is not None,
            'INSTALLED_APK_PATH_INVALID')
    return path

def apk_hash(serial,path):
    if not path:return None
    out=adb(serial,'shell','sha256sum',path)
    match=re.match(r'^([0-9a-fA-F]{64})\s+',out)
    require(match is not None,'INSTALLED_APK_HASH_UNAVAILABLE')
    return match.group(1).lower()

def inspect(serial,apk,attestation):
    require(re.fullmatch(r'[A-Za-z0-9._:-]{1,100}',serial) is not None,'DEVICE_SERIAL_INVALID')
    require(apk.is_file() and not apk.is_symlink() and 100_000 < apk.stat().st_size < 1_073_741_824,
            'HOSTED_APK_UNSAFE')
    require(attestation.is_file() and not attestation.is_symlink() and 20 < attestation.stat().st_size < 65536,
            'HOSTED_ATTESTATION_UNSAFE')
    data=json.loads(attestation.read_text())
    digest=sha256_file(apk)
    require(data.get('schema')=='cbnx06-full-cinderbox-lab-v1' and
            data.get('application_id')==LAB and
            data.get('apk_sha256')==digest and
            re.fullmatch(r'[0-9a-f]{40}',str(data.get('source_sha',''))) is not None and
            re.fullmatch(r'[0-9a-f]{64}',str(data.get('certificate_sha256',''))) is not None and
            data.get('lab_isolated_build') is True and
            data.get('physical_qualified') is False,
            'HOSTED_APK_ATTESTATION_MISMATCH')
    sdk=adb(serial,'shell','getprop','ro.build.version.sdk')
    abi=adb(serial,'shell','getprop','ro.product.cpu.abi')
    emulator=adb(serial,'shell','getprop','ro.kernel.qemu')
    require(re.fullmatch(r'\d{1,3}',sdk) is not None and re.fullmatch(r'[a-zA-Z0-9._-]{1,60}',abi) is not None,
            'DEVICE_PROPERTIES_INVALID')
    prod_path=apk_path(serial,PROD)
    prod_before=apk_hash(serial,prod_path)
    lab_path=apk_path(serial,LAB)
    lab_hash=apk_hash(serial,lab_path)
    prod_after=apk_hash(serial,prod_path)
    # No false claim: absent lab, unhashable production, non-physical ABI/SDK,
    # or unmatched bytes means inspection-only, never qualified.
    pass_read_only=(sdk=='36' and abi=='arm64-v8a' and emulator!='1' and
                    prod_before is not None and prod_before==prod_after and
                    lab_hash is not None and lab_hash==digest)
    return {
        'schema':'cbnx06-lab02b-device-read-only-v1',
        'mode':'adb-read-only-no-install', 'source_sha':data['source_sha'],
        'device_api':int(sdk),'device_abi':abi,'emulator_flag':emulator,
        'production_package':PROD,'production_apk_sha256_before':prod_before,
        'production_apk_sha256_after':prod_after,
        'lab_package':LAB,'lab_apk_sha256_installed':lab_hash,
        'lab_apk_sha256_hosted':digest,'lab_signer_sha256_hosted':data['certificate_sha256'],
        'physical_read_only_package_identity_qualified':pass_read_only,
        'game_files_unchanged_qualified':False,
        'live_nexus_qualified':False,'install_rollback_qualified':False,
        'release_qualified':False,
        'note':'Package/byte read-only evidence only. Does not inspect or prove game-file immutability.'
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',default='localhost:5555')
    parser.add_argument('--apk',required=True,type=Path)
    parser.add_argument('--attestation',required=True,type=Path)
    parser.add_argument('--ack',required=True,choices=['I_AUTHORIZE_READ_ONLY_DEVICE_PROBE'])
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        report=inspect(args.serial,args.apk,args.attestation)
        print('CBNX06_LAB02B_READ_ONLY_DEVICE_'+('PACKAGE_IDENTITY_PASS' if report['physical_read_only_package_identity_qualified'] else 'INSPECTION_ONLY_NOT_QUALIFIED'))
        if args.report is not None:
            path=args.report.expanduser().resolve()
            require(not path.exists() and path.parent.is_dir() and not path.parent.is_symlink(),
                    'REPORT_PATH_NOT_SAFE_OR_ALREADY_EXISTS')
            path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
            print('CBNX06_LAB02B_LOCAL_REPORT='+str(path))
        else:
            print(json.dumps(report,indent=2,sort_keys=True))
    except (Refused,OSError,ValueError,json.JSONDecodeError) as e:
        print('CBNX06_LAB02B_REFUSED:'+str(e),file=sys.stderr)
        raise SystemExit(2)
if __name__=='__main__':main()
