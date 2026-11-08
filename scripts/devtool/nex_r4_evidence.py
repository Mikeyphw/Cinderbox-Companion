#!/usr/bin/env python3
"""Checks actual emulator PNGs and emits bounded, synthetic-only source receipt."""
from __future__ import annotations
import hashlib,json,struct,sys
from pathlib import Path
STAGES=('saved-card','offline-sheet')
DIMENSIONS={393:(786,1704),360:(720,1600)}

def inspect(root: Path, source_sha: str, run_id: str):
    if not isinstance(source_sha,str) or len(source_sha)!=40 or not all(c in '0123456789abcdef' for c in source_sha):
        raise ValueError('NEX_R4_SOURCE_SHA_INVALID')
    if not run_id.isdigit() or not run_id:
        raise ValueError('NEX_R4_RUN_ID_INVALID')
    expected={f'{stage}-{width}.png' for stage in STAGES for width in DIMENSIONS}
    observed={f.name for f in root.iterdir() if f.is_file() and not f.name.startswith('.')}
    if observed!=expected:
        raise ValueError('NEX_R4_IMAGE_INVENTORY_MISMATCH')
    images={}
    for width,(w,h) in DIMENSIONS.items():
        for stage in STAGES:
            name=f'{stage}-{width}.png'
            data=(root/name).read_bytes()
            if not (len(data)>2500 and data[:8]==b'\x89PNG\r\n\x1a\n' and data[12:16]==b'IHDR'):
                raise ValueError('NEX_R4_PNG_INVALID:'+name)
            if struct.unpack('>II',data[16:24]) != (w,h):
                raise ValueError('NEX_R4_PNG_DIMENSIONS_INVALID:'+name)
            if b'IEND' not in data[-64:]:
                raise ValueError('NEX_R4_PNG_TRUNCATED:'+name)
            images[name]=hashlib.sha256(data).hexdigest()
    return {'schema':'nex-r4-offline-saved-v1','source_sha':source_sha,'github_run_id':run_id,
        'provider_responses_are_synthetic':True,'offline_saved_metadata_only':True,
        'real_nexus_account_qualified':False,'real_device_qualified':False,
        'release_approved':False,'images_sha256':images}

def main():
    root=Path(sys.argv[1]);sha=sys.argv[2];run=sys.argv[3]
    receipt=inspect(root,sha,run)
    (root/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('NEX_R4_SCREENSHOT_EVIDENCE_VERIFIED')
if __name__=='__main__': main()
