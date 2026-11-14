#!/usr/bin/env python3
"""Attest exact hosted LAB APK without equating it to production app identity."""
import argparse, hashlib, json, pathlib, re, shutil, stat, subprocess, sys

PKG='com.sdvsync.cbnx06lab'
class Refused(Exception):pass

def ensure(b, why):
    if not b:raise Refused(why)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify_signer(output):
    ensure(re.search(r'(?m)^Verified using v2 scheme \(APK Signature Scheme v2\): true\s*$',output) is not None,
           'APK_V2_REQUIRED')
    records=[]
    for line in output.splitlines():
        if 'certificate SHA-256 digest:' not in line or 'Source Stamp Signer' in line:continue
        m=re.fullmatch(r'(?:Signer #([1-9]\d*) certificate SHA-256 digest: |V(?:1|2|3|3\.0|3\.1) Signer: certificate SHA-256 digest: )([A-Fa-f0-9]{64})',line.strip())
        ensure(m is not None,'APK_SIGNER_LABEL_UNRECOGNIZED')
        records.append((m.group(1),m.group(2).lower()))
    ensure(records and len({x[1] for x in records})==1,'APK_SIGNERS_NOT_ONE_CERTIFICATE')
    legacy=[i for i,_ in records if i is not None]
    ensure(not legacy or (legacy==['1'] and len(records)==1),'APK_LEGACY_SIGNER_COUNT_NOT_ONE')
    if not legacy:
        # V2 is required, and each scheme may describe exactly one signer.
        # Duplicated lines are NOT proof of a single application signer.
        scheme_labels=[line.strip().split(' Signer:')[0] for line in output.splitlines()
                       if ' Signer: certificate SHA-256 digest:' in line and
                       'Source Stamp Signer' not in line]
        ensure(scheme_labels.count('V2')==1 and len(set(scheme_labels))==len(scheme_labels),
               'APK_SCHEME_SIGNER_COUNT_NOT_ONE')
    return records[0][1]

def attest(debug, out, source, apksigner, aapt):
    ensure(re.fullmatch('[0-9a-f]{40}',source) is not None,'SOURCE_INVALID')
    ensure(debug.is_dir() and not debug.is_symlink(),'GRADLE_DEBUG_DIR_UNSAFE')
    metadata=debug/'output-metadata.json'
    ensure(metadata.is_file() and not metadata.is_symlink(),'METADATA_MISSING')
    data=json.loads(metadata.read_text())
    ensure(data.get('applicationId')==PKG and data.get('variantName')=='cbnxLab','PACKAGE_VARIANT_MISMATCH')
    outputs=data.get('elements')
    ensure(type(outputs) is list and len(outputs)==1 and outputs[0].get('type')=='SINGLE' and
           outputs[0].get('filters')==[],'UNEXPECTED_APK_SPLITS')
    name=outputs[0].get('outputFile')
    ensure(type(name) is str and re.fullmatch(r'CinderboxCompanion-v[A-Za-z0-9._+-]{1,80}\.apk',name),'FILENAME_UNEXPECTED')
    apk=debug/name
    ensure(apk.is_file() and not apk.is_symlink() and apk.stat().st_size>100_000 and
           len(list(debug.glob('*.apk')))==1,'APK_MISSING_OR_MULTIPLE')
    ensure(not out.exists() and not out.is_symlink(),'OUTPUT_EXISTS')
    dump=subprocess.run([str(aapt),'dump','badging',str(apk)],capture_output=True,text=True,check=True).stdout
    ensure("package: name='com.sdvsync.cbnx06lab'" in dump and "application-label:'Cinderbox LAB'" in dump,
           'APK_PACKAGE_OR_LABEL_MISMATCH')
    permissions=subprocess.run([str(aapt),'dump','permissions',str(apk)],capture_output=True,text=True,check=True).stdout
    for blocked in ('MANAGE_EXTERNAL_STORAGE','REQUEST_INSTALL_PACKAGES','READ_EXTERNAL_STORAGE',
                    'WRITE_EXTERNAL_STORAGE'):
        ensure('android.permission.'+blocked not in permissions,'APK_PRIVILEGED_PERMISSION:'+blocked)
    manifest=subprocess.run([str(aapt),'dump','xmltree',str(apk),'AndroidManifest.xml'],capture_output=True,text=True,check=True).stdout
    for blocked in ('nxm','SteamBackgroundService','AutoSyncService','GameDownloadService',
                    'SyncStatusWidgetReceiver','ShizukuProvider'):
        ensure(blocked not in manifest,'APK_FORBIDDEN_COMPONENT:'+blocked)
    signer=subprocess.run([str(apksigner),'verify','--verbose','--print-certs',str(apk)],
                          capture_output=True,text=True,check=True).stdout
    cert=verify_signer(signer)
    out.mkdir(mode=0o700,parents=True)
    dest=out/'app-cbnxlab-debug.apk'
    shutil.copyfile(apk,dest)
    ensure(sha(dest)==sha(apk),'APK_COPY_MISMATCH')
    digest=sha(dest)
    (out/'SHA256SUMS').write_text(f'{digest}  app-cbnxlab-debug.apk\n')
    record={'schema':'cbnx06-full-cinderbox-lab-v1','source_sha':source,
            'application_id':PKG,'apk_sha256':digest,'certificate_sha256':cert,
            'lab_isolated_build':True,'source_attested':True,
            'physical_qualified':False,'live_nexus_qualified':False,
            'rollback_qualified':False,'release_qualified':False,
            'installed_apk_bytes_verified_equal':False}
    (out/'LAB_ARTIFACT_ATTESTATION.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print('CBNX06_FULL_LAB_HOSTED_APK_SIGNER_AND_MANIFEST_PASS='+digest)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--debug-dir',required=True,type=pathlib.Path)
    p.add_argument('--output-dir',required=True,type=pathlib.Path)
    p.add_argument('--source-sha',required=True)
    p.add_argument('--apksigner',required=True,type=pathlib.Path)
    p.add_argument('--aapt',required=True,type=pathlib.Path)
    a=p.parse_args()
    try:attest(a.debug_dir,a.output_dir,a.source_sha,a.apksigner,a.aapt)
    except (Refused,ValueError,OSError,subprocess.CalledProcessError) as e:
        print('CBNX06_FULL_LAB_ARTIFACT_REFUSED:'+str(e),file=sys.stderr);raise SystemExit(2)
