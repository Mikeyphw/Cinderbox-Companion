#!/usr/bin/env python3
"""CB-NX06: physical Android API36 read-only exact-file acceptance witness.

Read-only ADB; credentials, NXM URLs, raw journals, raw property files,
app-private paths, and filenames are NEVER persisted or printed. No install,
delete, root, grant, pairing, curl or network API calls. Live Nexus browser
proof and release qualification ALWAYS remain independent and unqualified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import stat
import uuid
import xml.etree.ElementTree as ET

APP = 'com.sdvsync'
BROWSERS = ('io.github.forkmaintainers.iceraven', 'org.mozilla.firefox',
            'org.mozilla.firefox_beta', 'org.mozilla.fennec_fdroid')
MODS = '/storage/emulated/0/StardewValley/desktop/Mods'
SERIAL = re.compile(r'(?:localhost|127\.0\.0\.1):[0-9]{2,5}\Z')
ID = re.compile(r'[1-9][0-9]{0,11}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
UUID = re.compile(r'[0-9a-fA-F-]{36}\Z')
REQUEST = re.compile(r'[A-Za-z0-9_-]{22,64}\Z')
ACK = 'I_AUTHORIZE_READ_ONLY_DEVICE_PROBE'
JOURNAL = 'shared_prefs/cinderbox_mod_download_journal_v1.xml'
INBOX = 'shared_prefs/cbnx03b_pairing_inbox.xml'
PENDING_ZIP = 'files/mod-review-pending.zip'
PENDING_PROPS = 'files/mod-review-pending.properties'
MAX_READ = 4_000_000
KNOWN = {'QUEUED','DOWNLOADING','VALIDATING','INSTALLING','REVIEW_REQUIRED',
         'BLOCKED','VERIFY_REQUIRED','PAUSED','INTERRUPTED','FAILED','CANCELLED',
         'DISCARDED','INSTALLED','COMPLETED'}
STAGED = {'REVIEW_REQUIRED'}  # BLOCKED or uncertain is not a safe ready-for-review result
SCHEMA = 'cbnx06-physical-read-only-v1'


class Refusal(Exception):
    pass


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def positive(value: str) -> bool:
    return isinstance(value, str) and ID.fullmatch(value) is not None


def parse_prefs(raw: bytes | None, key: str, *, missing_ok: bool) -> str | None:
    if raw is None:
        if missing_ok: return None
        raise Refusal('PRIVATE_PREFS_MISSING:' + key)
    if len(raw) > 256_000:
        raise Refusal('PRIVATE_PREFS_OVERSIZED:' + key)
    try:
        root = ET.fromstring(raw)
        if root.tag != 'map': raise ValueError('not map')
        entries = [e for e in root if e.attrib.get('name') == key]
        if len(entries) != 1 or entries[0].tag != 'string': raise ValueError('missing key')
        return entries[0].text if entries[0].text is not None else ''
    except (ET.ParseError, ValueError) as exc:
        raise Refusal('PRIVATE_PREFS_UNREADABLE:' + key) from exc


def journal_rows(raw: bytes | None) -> list[dict]:
    value = parse_prefs(raw, 'records', missing_ok=True)
    if value is None: return []
    try:
        rows = json.loads(value)
        if not isinstance(rows,list) or len(rows) > 80: raise ValueError('rows')
        result=[]
        seen=set()
        for r in rows:
            if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not UUID.fullmatch(r['id']):
                raise ValueError('id')
            if r['id'] in seen or r.get('status') not in KNOWN: raise ValueError('status')
            seen.add(r['id'])
            created=r.get('created')
            if type(created) is not int or created<=0:raise ValueError('timestamp')
            src,mod,file = r.get('source'),str(r.get('modId','')),str(r.get('fileId',''))
            if src == 'nexus' and (not positive(mod) or not positive(file)): raise ValueError('nexus identity')
            result.append({'id':r['id'],'source':src,'mod':mod,'file':file,
                           'status':r['status'],'created':created})
        return result
    except (ValueError, TypeError, KeyError) as exc:
        raise Refusal('DOWNLOAD_JOURNAL_CORRUPT_OR_UNKNOWN') from exc


def inbox_rows(raw: bytes | None) -> list[dict]:
    value = parse_prefs(raw,'requests_v1',missing_ok=True)
    if value is None: return []
    try:
        rows=json.loads(value)
        if not isinstance(rows,list) or len(rows)>40: raise ValueError('size')
        out=[]; seen=set()
        for r in rows:
            if not isinstance(r,dict): raise ValueError('record')
            request=r.get('id','')
            if (not isinstance(request,str) or not REQUEST.fullmatch(request)
                    or request in seen or r.get('status') not in ('PENDING','OPENED','DISMISSED')
                    or not positive(r.get('mod_id')) or not positive(r.get('file_id'))):
                raise ValueError('record identity')
            seen.add(request)
            created=r.get('created_at')
            if type(created) is not int or created<=0: raise ValueError('timestamp')
            out.append({'id_hash':digest(request.encode()),'mod':r['mod_id'],'file':r['file_id'],
                        'status':r['status'],'created':created})
        return out
    except (ValueError, TypeError, KeyError) as exc:
        raise Refusal('PAIRING_INBOX_CORRUPT_OR_UNKNOWN') from exc


def receipt_properties(raw: bytes) -> dict:
    if not 1<=len(raw)<=32768: raise Refusal('REVIEW_PROPS_SIZE_INVALID')
    # The native Java Properties writer uses ordinary key=value for these
    # safe machine fields; refuse escaped/multiline values instead of guessing.
    allowed={'source','mod_id','file_id','job_id','sha256'}
    out={}
    for line in raw.decode('utf-8','replace').splitlines():
        if not line or line.startswith(('#','!')): continue
        name,sep,val=line.partition('=')
        if not sep or not name or name in out: raise Refusal('REVIEW_PROPS_MALFORMED')
        if name in allowed: out[name]=val.strip()
    if (out.get('source')!='nexus' or not positive(out.get('mod_id'))
        or not positive(out.get('file_id')) or not UUID.fullmatch(out.get('job_id',''))
        or not HEX64.fullmatch(out.get('sha256',''))):
        raise Refusal('REVIEW_RECEIPT_EXACT_IDENTITY_UNAVAILABLE')
    return out


class Adb:
    def __init__(self,serial: str,executable='adb'):
        if not SERIAL.fullmatch(serial): raise Refusal('EXPLICIT_LOOPBACK_ADB_SERIAL_REQUIRED')
        self.serial=serial; self.executable=executable

    def run(self,*args: str,optional=False,timeout=45,max_bytes=MAX_READ)->bytes|None:
        # Callers only use the audited fixed read-only commands in this file.
        try:
            r=subprocess.run([self.executable,'-s',self.serial,*args],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             timeout=timeout,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise Refusal('ADB_READ_ONLY_PROBE_TIMEOUT_OR_MISSING') from exc
        if len(r.stdout)>max_bytes or len(r.stderr)>32768: raise Refusal('ADB_RESPONSE_TOO_LARGE')
        if r.returncode:
            if optional:return None
            # Never include stderr, it may contain paths or secrets.
            raise Refusal('ADB_READ_ONLY_COMMAND_FAILED:'+args[0])
        return r.stdout

    def text(self,*args: str,optional=False)->str|None:
        b=self.run(*args,optional=optional)
        return None if b is None else b.decode('utf8','replace').strip()

    def prop(self,name:str)->str:
        return self.text('shell','getprop',name) or ''

    def private_exists(self,path:str)->bool:
        # Symlinks must never be attested as app-private, regular files.
        if self.run('shell','run-as',APP,'test','-L',path,optional=True) is not None:
            raise Refusal('APP_PRIVATE_SYMLINK_REFUSED')
        # The only allowed read-only existence checks. Do not cat huge ZIPs.
        exists=self.run('shell','run-as',APP,'test','-f',path,optional=True)
        if exists is None:
            if self.run('shell','run-as',APP,'test','-e',path,optional=True) is not None:
                raise Refusal('APP_PRIVATE_FILE_NOT_REGULAR_OR_UNREADABLE')
            return False
        return True

    def private(self,path:str,optional=False)->bytes|None:
        # Test existence independently; permission errors are NOT 'missing'.
        exists=self.private_exists(path)
        if not exists:
            if optional:return None
            raise Refusal('APP_PRIVATE_FILE_ABSENT')
        return self.run('shell','run-as',APP,'cat',path)


def physical(adb:Adb)->dict:
    if adb.text('get-state')!='device': raise Refusal('ADB_DEVICE_NOT_READY')
    sdk=adb.prop('ro.build.version.sdk'); abi=adb.prop('ro.product.cpu.abi')
    hardware=adb.prop('ro.hardware').lower()
    model=adb.prop('ro.product.model').lower()
    fingerprint=adb.prop('ro.build.fingerprint').lower()
    if (sdk!='36' or not abi.startswith('arm64') or
        adb.prop('ro.kernel.qemu') not in ('','0') or
        adb.prop('ro.boot.qemu') not in ('','0') or
        any(s in hardware for s in ('ranchu','goldfish','cuttlefish','vbox','qemu')) or
        any(s in model for s in ('sdk_gphone','android sdk built','emulator')) or
        any(s in fingerprint for s in ('generic_x86','sdk_gphone','emulator'))):
        raise Refusal('PHYSICAL_ARM64_API36_REQUIRED_NO_EMULATOR')
    browser=[p for p in BROWSERS if adb.text('shell','pm','path',p,optional=True)]
    if not browser: raise Refusal('FIREFOX_OR_ICERAVEN_APP_REQUIRED')
    paths=adb.text('shell','pm','path',APP) or ''
    base=[s.removeprefix('package:') for s in paths.splitlines() if s.startswith('package:') and s.endswith('/base.apk')]
    if len(base)!=1 or not base[0].startswith('/data/app/'):
        raise Refusal('CINDERBOX_APP_BASE_APK_NOT_INSTALLED')
    a=adb.text('shell','sha256sum',base[0]) or ''
    match=re.match(r'([a-f0-9]{64})\s',a)
    if not match:raise Refusal('CINDERBOX_INSTALLED_BASE_APK_SHA_UNAVAILABLE')
    if adb.text('shell','run-as',APP,'id',optional=True) is None:
        raise Refusal('CINDERBOX_DEBUG_RUN_AS_REQUIRED_NO_ROOT_FALLBACK')
    return {'physical_arm64_api36':True,'android_api':36,'installed_cinderbox_apk_sha256':match.group(1),
            'gecko_browser_packages':sorted(browser),'installed_extension_proven':False,
            'no_emulator_flags':True}


def mods_fingerprint(adb:Adb,full=False)->dict:
    listing=adb.run('shell','ls','-laR',MODS)
    if not listing or not listing.strip(): raise Refusal('STARDew_MODS_DIRECTORY_NOT_ACCESSIBLE')
    result={'metadata_listing_sha256':digest(listing),'file_byte_proof':False,
            'full_contents_sha256':None}
    if full:
        # The shell command is a compile-time constant; no user-provided paths.
        # Hash every file, sorted locally; never write/print filenames or data.
        command='cd /storage/emulated/0/StardewValley/desktop/Mods && find . -type f -exec sha256sum {} +'
        listing=adb.run('shell',command,timeout=240,max_bytes=12_000_000)
        if listing is None: raise Refusal('MODS_CONTENT_HASH_FAILED')
        rows=listing.splitlines()
        if len(rows)>100000 or any(re.fullmatch(rb'[0-9a-f]{64}  [^\x00\r\n]+',row) is None for row in rows):
            raise Refusal('MODS_CONTENT_HASH_OUTPUT_UNSAFE_OR_AMBIGUOUS')
        normalized=b'\n'.join(sorted(rows))
        result['file_byte_proof']=True
        result['full_contents_sha256']=digest(normalized)
    return result


def private_snapshot(adb:Adb,mod:str,file:str)->dict:
    inbox=inbox_rows(adb.private(INBOX,optional=True))
    journal=journal_rows(adb.private(JOURNAL,optional=True))
    matching_inbox=[x for x in inbox if x['mod']==mod and x['file']==file]
    matching_journal=[x for x in journal if x['source']=='nexus' and x['mod']==mod and x['file']==file]
    # Never read an archive into ADB memory: files can approach 1 GiB.
    a=adb.private_exists(PENDING_ZIP)
    p=adb.private(PENDING_PROPS,optional=True)
    if a != (p is not None): raise Refusal('PARTIAL_PRIVATE_REVIEW_STAGING')
    pending={'present':False}
    if a:
        # The private archive is bounded to 1 GiB by the production downloader.
        # Inspect content by hash, but DO NOT read/stage it to host storage.
        receipt=receipt_properties(p)
        line=adb.text('shell','run-as',APP,'sha256sum',PENDING_ZIP) or ''
        h=re.match(r'([a-f0-9]{64})\s',line)
        sz=adb.text('shell','run-as',APP,'wc','-c',PENDING_ZIP) or ''
        size=re.match(r'\s*(\d+)\s',sz)
        if not h or not size or not 1<=int(size.group(1))<=1_073_741_824:
            raise Refusal('REVIEW_ARCHIVE_SHA_OR_SIZE_INVALID')
        pending={'present':True,'sha256':h.group(1),'bytes':int(size.group(1)),
                 'receipt_matches_archive':h.group(1)==receipt['sha256'],
                 'source':receipt['source'],'mod':receipt['mod_id'],'file':receipt['file_id'],
                 'job_id':receipt['job_id']}
    return {'inbox':matching_inbox,'journal':matching_journal,'review':pending,
            'journal_count':len(journal),'inbox_count':len(inbox)}


def snapshot(adb:Adb,mod:str,file:str,full=False)->dict:
    return {'device':physical(adb),'mods':mods_fingerprint(adb,full),
            'private':private_snapshot(adb,mod,file)}


def assess(before:dict,after:dict)->dict:
    """Conservative machine-only judgement: never assert real browser/auth/release."""
    reasons=[]
    def bad(code,condition):
        if condition:reasons.append(code)
    mod,file=before['selected_mod_id'],before['selected_file_id']
    old,new=before['snapshot'],after
    bad('DEVICE_OR_APK_CHANGED',old['device']!=new['device'])
    bad('MODS_METADATA_CHANGED_BEFORE_REVIEW',old['mods']['metadata_listing_sha256']!=new['mods']['metadata_listing_sha256'])
    content_proven=bool(old['mods']['file_byte_proof'] and new['mods']['file_byte_proof'] and
                        old['mods']['full_contents_sha256']==new['mods']['full_contents_sha256'])
    if old['mods']['file_byte_proof']!=new['mods']['file_byte_proof']:
        bad('CONTENT_HASH_MODE_CHANGED',True)
    if old['mods']['file_byte_proof'] and not content_proven:
        bad('MODS_CONTENT_CHANGED_BEFORE_REVIEW',True)
    old_inbox={x['id_hash'] for x in old['private']['inbox']}
    fresh=[x for x in new['private']['inbox'] if x['id_hash'] not in old_inbox]
    bad('NO_NEW_EXACT_FILE_PAIRING_REQUEST',not fresh)
    bad('PAIRING_REQUEST_IDENTITY_NOT_FRESH',any(x['created'] < before['captured_epoch_ms']-5000 for x in fresh))
    pending=new['private']['review']
    bad('REVIEW_ARCHIVE_NOT_STAGED',not pending.get('present'))
    qualified_archive=False
    if pending.get('present'):
        bad('REVIEW_RECEIPT_MOD_OR_FILE_MISMATCH',pending.get('source')!='nexus' or pending.get('mod')!=mod or pending.get('file')!=file)
        bad('REVIEW_ARCHIVE_CHECKSUM_MISMATCH',pending.get('receipt_matches_archive') is not True)
        matching=[j for j in new['private']['journal'] if j['id']==pending['job_id']]
        bad('NO_MATCHING_JOURNAL_AND_REVIEW',len(matching)!=1 or matching[0]['status'] not in STAGED)
        old_ids={j['id'] for j in old['private']['journal']}
        bad('REUSED_PREEXISTING_JOURNAL_JOB',pending['job_id'] in old_ids)
        qualified_archive=(pending.get('source')=='nexus' and pending.get('mod')==mod and
                          pending.get('file')==file and pending.get('receipt_matches_archive') is True
                          and len(matching)==1 and matching[0]['status'] in STAGED and pending['job_id'] not in old_ids)
    # No action here ever installs, modifies or approves a mod.
    return {'status':('EXACT_FILE_PRIVATE_STAGING_WITNESSED' if not reasons and qualified_archive
                      else 'INCONCLUSIVE_NOT_QUALIFIED'),
            'reason_codes':sorted(set(reasons)),
            'pairing_request_machine_observed':bool(fresh),
            'private_archive_receipt_and_journal_matched':bool(qualified_archive),
            'mods_metadata_listing_unchanged':old['mods']['metadata_listing_sha256']==new['mods']['metadata_listing_sha256'],
            'mods_file_byte_contents_unchanged_proven':content_proven,
            'actual_firefox_extension_installed_proven':False,
            'live_nexus_authentication_proven':False,
            'browser_action_independently_proven':False,
            'safe_install_and_rollback_physically_qualified':False,
            'live_nexus_qualified':False,'release_qualified':False}


def private_write(path:Path,obj:dict):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.parent.is_symlink() or stat.S_IMODE(path.parent.stat().st_mode)&0o077:
        raise Refusal('EVIDENCE_DIRECTORY_MUST_BE_PRIVATE_0700')
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,'O_NOFOLLOW'):flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as f:
        json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=True)
        f.write('\n')


def safe_load(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>60000:
        raise Refusal('INVALID_OR_SYMLINK_SESSION_FILE')
    obj=json.loads(path.read_text(encoding='utf8'))
    if not isinstance(obj,dict) or obj.get('schema')!=SCHEMA: raise Refusal('INVALID_RECEIPT_SCHEMA')
    return obj


def start(args,adb:Adb):
    if not positive(args.mod_id) or not positive(args.file_id):
        raise Refusal('POSITIVE_EXACT_MOD_AND_FILE_IDS_REQUIRED')
    if not args.apk_file or not args.apk_attestation:
        raise Refusal('EXACT_CI_DEBUG_APK_AND_SOURCE_ATTESTATION_FILES_REQUIRED')
    apk_path=Path(args.apk_file).expanduser()
    attest_path=Path(args.apk_attestation).expanduser()
    if (apk_path.is_symlink() or not apk_path.is_file() or apk_path.suffix!='.apk'
        or not 1<=apk_path.stat().st_size<=400_000_000 or attest_path.is_symlink()
        or not attest_path.is_file() or attest_path.stat().st_size>16384):
        raise Refusal('CI_DEBUG_APK_OR_ATTESTATION_FILE_INVALID')
    h=hashlib.sha256()
    with apk_path.open('rb') as f:
        for block in iter(lambda:f.read(131072),b''):h.update(block)
    expected=h.hexdigest()
    try:
        meta=json.loads(attest_path.read_text(encoding='utf8'))
    except (ValueError,UnicodeError) as exc:
        raise Refusal('CI_SOURCE_ATTESTATION_INVALID_JSON') from exc
    if (not isinstance(meta,dict) or meta.get('schema')!='cbnx06-hosted-debug-apk-v1'
        or meta.get('source_sha')!=args.cinderbox_sha or meta.get('apk_sha256')!=expected
        or any(meta.get(key) is not False for key in (
            'physical_arm64_qualified','live_firefox_qualified',
            'live_nexus_qualified','release_qualified'))):
        raise Refusal('CI_DEBUG_APK_SOURCE_SHA_OR_BYTES_NOT_ATTESTED')
    if args.apk_sha256 and args.apk_sha256!=expected:
        raise Refusal('CI_APK_USER_EXPECTED_SHA_MISMATCH')
    directory=Path(args.evidence_dir).expanduser().resolve()
    if directory.exists() and list(directory.iterdir()):
        raise Refusal('EVIDENCE_DIRECTORY_MUST_BE_EMPTY')
    snap=snapshot(adb,args.mod_id,args.file_id,args.full_mods_hash)
    if snap['device']['installed_cinderbox_apk_sha256']!=expected:
        raise Refusal('INSTALLED_APK_DOES_NOT_MATCH_PINNED_DEBUG_ARTIFACT')
    if snap['private']['review']['present']:raise Refusal('PREEXISTING_PRIVATE_REVIEW_MUST_BE_RESOLVED_MANUALLY')
    if any(x['status']=='PENDING' for x in snap['private']['inbox']):
        raise Refusal('PREEXISTING_EXACT_FILE_PAIRING_REQUEST')
    if any(x['status'] in ('QUEUED','DOWNLOADING','VALIDATING','INSTALLING','REVIEW_REQUIRED','BLOCKED','PAUSED','VERIFY_REQUIRED') for x in snap['private']['journal']):
        raise Refusal('PREEXISTING_EXACT_FILE_UNRESOLVED_JOB')
    epoch=int(datetime.now(timezone.utc).timestamp()*1000)
    obj={'schema':SCHEMA,'phase':'before','session':uuid.uuid4().hex,'captured_at':utc(),
         'captured_epoch_ms':epoch,'selected_mod_id':args.mod_id,'selected_file_id':args.file_id,
         'expected_ci_debug_apk_sha256':expected,
         'ci_debug_apk_bytes_locally_hashed':True,
         'ci_debug_apk_source_attestation_verified':True,
         'snapshot':snap,'source_pins':{'cinderbox':args.cinderbox_sha,'firefox':args.firefox_sha},
         'live_nexus_qualified':False,'release_qualified':False}
    private_write(directory/'before.json',obj)
    print('CBNX06_PHYSICAL_BEFORE_READ_ONLY_CAPTURE_PASS')
    print('Next: pair the actual Firefox/Iceraven extension manually, enable exact-file handoff locally,')
    print('select only the declared Nexus mod/file, complete legitimate Nexus authorization,')
    print('and stop at Cinderbox review WITHOUT approving/installing. Then run device after.')


def finish(args,adb:Adb):
    d=Path(args.evidence_dir).expanduser().resolve()
    b=safe_load(d/'before.json')
    if b.get('phase')!='before' or not re.fullmatch(r'[a-f0-9]{32}',b.get('session','')):
        raise Refusal('INVALID_BEFORE_RECEIPT')
    for key in ('cinderbox','firefox'):
        if b.get('source_pins',{}).get(key)!=getattr(args,key+'_sha'):
            raise Refusal('SOURCE_PIN_CHANGED_DURING_PHYSICAL_ACCEPTANCE')
    stamp=digest(canonical(b))
    after=snapshot(adb,b['selected_mod_id'],b['selected_file_id'],b['snapshot']['mods']['file_byte_proof'])
    if after['device']['installed_cinderbox_apk_sha256']!=b.get('expected_ci_debug_apk_sha256'):
        raise Refusal('INSTALLED_APK_CHANGED_DURING_ACCEPTANCE')
    result=assess(b,after)
    receipt={'schema':SCHEMA,'phase':'after','session':b['session'],
             'before_canonical_sha256':stamp,'captured_at':utc(),
             'source_pins':b['source_pins'],'snapshot':after,'evaluation':result,
             'manual_firefox_iceraven_nexus_evidence_required':True,
             'live_nexus_qualified':False,'release_qualified':False}
    file=d/('after-'+uuid.uuid4().hex[:12]+'.json')
    private_write(file,receipt)
    print('CBNX06_PHYSICAL_AFTER_'+result['status'])
    if result['reason_codes']:print('CBNX06_SAFE_REASON_CODES='+','.join(result['reason_codes']))
    print('CBNX06_BROWSER_LOGIN_AND_INSTALL_ROLLBACK_NOT_AUTOMATICALLY_QUALIFIED')
    print('CBNX06_PRIVATE_RECEIPT_SAVED='+str(file))
    return 0 if result['status']=='EXACT_FILE_PRIVATE_STAGING_WITNESSED' else 1


def cli(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['preflight','before','after'])
    p.add_argument('--serial',default='localhost:5555')
    p.add_argument('--ack',required=True)
    p.add_argument('--evidence-dir',default=str(Path.home()/'.local/share/cbnx06-acceptance'))
    p.add_argument('--mod-id');p.add_argument('--file-id')
    p.add_argument('--apk-sha256')
    p.add_argument('--apk-file',help='Locally downloaded CI debug APK, never installed by this tool')
    p.add_argument('--apk-attestation',help='SOURCE_ATTESTATION.json downloaded alongside exact CI APK')
    p.add_argument('--full-mods-hash',action='store_true')
    p.add_argument('--cinderbox-sha',help='Exact Cinderbox PR commit (required for before/after)')
    p.add_argument('--firefox-sha',help='Exact Firefox PR commit (required for before/after)')
    a=p.parse_args(argv)
    if a.ack!=ACK:raise Refusal('EXPLICIT_READ_ONLY_DEVICE_PROBE_ACK_REQUIRED')
    if a.phase!='preflight' and (not a.cinderbox_sha or not a.firefox_sha or
        not HEX40.fullmatch(a.cinderbox_sha) or not HEX40.fullmatch(a.firefox_sha)):
        raise Refusal('EXACT_BOTH_PR_HEAD_SHAS_REQUIRED')
    adb=Adb(a.serial)
    if a.phase=='preflight':
        device=physical(adb)
        print('CBNX06_PHYSICAL_READ_ONLY_PREFLIGHT_PASS')
        print('CBNX06_ANDROID_API='+str(device['android_api']))
        print('CBNX06_INSTALLED_APK_SHA256='+device['installed_cinderbox_apk_sha256'])
        print('CBNX06_GECKO_BROWSER_PACKAGES='+','.join(device['gecko_browser_packages']))
        print('CBNX06_NO_BROWSER_EXTENSION_OR_LIVE_NEXUS_QUALIFICATION')
        return 0
    if a.phase=='before':start(a,adb);return 0
    return finish(a,adb)


if __name__=='__main__':
    try:sys.exit(cli())
    except (Refusal,ValueError,TypeError,KeyError,ET.ParseError,PermissionError,OSError) as exc:
        code=str(exc) if isinstance(exc,Refusal) else 'INVALID_SESSION_OR_PRIVATE_EVIDENCE'
        print('CBNX06_REFUSED:'+code,file=sys.stderr)
        sys.exit(2)
