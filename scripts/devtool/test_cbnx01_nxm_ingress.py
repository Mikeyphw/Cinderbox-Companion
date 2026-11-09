#!/usr/bin/env python3
"""No Android runtime requirement. Inspect fail-closed, credential-free receipt source."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'app/src/main/java/com/sdvsync/MainActivity.kt').read_text(encoding='utf8')
gate=(ROOT/'scripts/devtool/cbnx01_gate.py').read_text(encoding='utf8')
for text in ('NXM_RECEIVED_VIEW','NXM_PARSE_REJECTED','NXM_PARSE_ACCEPTED',
             'NXM_URL_RESOLUTION_STARTED','NXM_MANAGER_RETURNED_NOT_STAGED_PROOF',
             'NXM_RESOLUTION_OR_DOWNLOAD_FAILURE','NXM_SINGLE_FLIGHT_BLOCKED'):
    assert text in src, f'MISSING_RECEIPT:{text}'
    assert text in gate or text in ('NXM_SINGLE_FLIGHT_BLOCKED',), f'GATE_MISSING:{text}'
assert src.count('private const val NXM_DIAG_TAG = "CBNX01_NXM_RX"')==1
logs=re.findall(r'Log\.i\(NXM_DIAG_TAG,\s*(.*?)\)',src,re.S)
assert len(logs)>=5, 'MISSING_RECEIPT_LOG_CALLS'
for code in logs:
    assert not any(secret in code for secret in ('uri.toString(', 'parsed.key', 'parsed.expires',
        'downloadUrl', 'url,', 'intent.data.toString(', 'e.message','requestId','fileId','modId')), 'POTENTIAL_SECRET_LOGGED'
assert 'NxmUriPolicy.parse(uri.toString())' in src
assert 'downloadManager.startDownload(url, modName, parsed.modId, "nexus")' in src
print('CBNX01_HF04_REDACTED_NXM_SOURCE_PASS')
