#!/usr/bin/env python3
"""Opt-in, read-only Nexus live schema check. Never logs credentials or provider data.

No network is used during ordinary PR source/JVM tests. This module only makes
network calls on an explicit invocation with CINDERBOX_NEXUS_API_KEY available.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
GRAPHQL = 'https://api.nexusmods.com/v2/graphql'
REST = 'https://api.nexusmods.com/v1/games/stardewvalley/mods/'
IDENTIFIER = re.compile(r'[1-9][0-9]{0,9}\Z')


class ProbeRefusal(RuntimeError):
    pass


def query_from_source(root: Path = ROOT) -> str:
    """Bind live probe to the *actual* Kotlin query, not a second guessed schema."""
    path = root/'app/src/main/java/com/sdvsync/mods/api/NexusCatalogOperation.kt'
    source = path.read_text(encoding='utf-8')
    match = re.search(r'document\s*=\s*"""(.*?)"""', source, flags=re.DOTALL)
    if not match or 'NEXUS_SEARCH_PAGE_SIZE' not in source:
        raise ProbeRefusal('SOURCE_QUERY_UNVERIFIABLE')
    query = match.group(1).replace("${'$'}", '$').replace('$NEXUS_SEARCH_PAGE_SIZE', '50')
    required = ('modCategory { name }', 'updatedAt', 'modId', 'totalCount',
                '$filter: ModsFilter!', '$sort: [ModsSort!]', '$offset: Int!', 'count: 50')
    if any(item not in query for item in required):
        raise ProbeRefusal('SOURCE_QUERY_CONTRACT_DRIFT')
    if '"gameId"' not in source or '"1303"' not in source or '"EQUALS"' not in source:
        raise ProbeRefusal('SOURCE_GAME_PIN_DRIFT')
    return query


def positive_id(value: object) -> str:
    if type(value) is not int or value > 2147483647 or not IDENTIFIER.fullmatch(str(value)):
        raise ProbeRefusal('PROVIDER_INVALID_MOD_ID')
    return str(value)


def validate_page(raw: object, offset: int) -> tuple[list[dict], int]:
    if not isinstance(raw, dict) or raw.get('errors'):
        raise ProbeRefusal('PROVIDER_GRAPHQL_SCHEMA_OR_AUTH_REJECTED')
    data = raw.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('mods'), dict):
        raise ProbeRefusal('PROVIDER_GRAPHQL_SHAPE_INVALID')
    mods = data['mods']
    count = mods.get('totalCount')
    nodes = mods.get('nodes')
    if type(count) is not int or not 0 <= count <= 2147483647:
        raise ProbeRefusal('PROVIDER_COUNT_INVALID')
    if not isinstance(nodes, list) or len(nodes) > 50 or len(nodes) + offset > count:
        raise ProbeRefusal('PROVIDER_PAGE_INVALID')
    for node in nodes:
        if not isinstance(node, dict):
            raise ProbeRefusal('PROVIDER_NODE_INVALID')
        positive_id(node.get('modId'))
        category = node.get('modCategory')
        if category is not None and (not isinstance(category, dict) or
                                    not isinstance(category.get('name'), str)):
            raise ProbeRefusal('PROVIDER_CATEGORY_SHAPE_INVALID')
        stamp = node.get('updatedAt')
        if stamp is not None:
            if not isinstance(stamp, str) or len(stamp) > 64:
                raise ProbeRefusal('PROVIDER_DATE_SHAPE_INVALID')
            try:
                value = dt.datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                if value.tzinfo is None: raise ValueError('timezone required')
            except ValueError:
                raise ProbeRefusal('PROVIDER_DATE_SHAPE_INVALID') from None
    return nodes, count


def request_json(url: str, key: str, body: dict | None = None) -> object:
    """Allowlisted read-only endpoints only. No headers, payloads, URLs in exceptions."""
    if url != GRAPHQL and not re.fullmatch(re.escape(REST)+r'[1-9][0-9]{0,9}(?:/files)?\.json', url):
        raise ProbeRefusal('ENDPOINT_NOT_ALLOWLISTED')
    encoded = None if body is None else json.dumps(body, separators=(',', ':')).encode('utf-8')
    if encoded is not None and len(encoded) > 12000:
        raise ProbeRefusal('REQUEST_TOO_LARGE')
    method = 'POST' if url == GRAPHQL else 'GET'
    req = urllib.request.Request(url, data=encoded, method=method, headers={
        'apikey': key, 'Application-Name': 'Cinderbox Companion',
        'User-Agent': 'Cinderbox-Companion/NEX-R2C-ReadOnly-Qualification',
        'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            # Never consume or persist unbounded user/provider responses.
            raw = response.read(1048577)
        if len(raw) > 1048576: raise ProbeRefusal('PROVIDER_RESPONSE_TOO_LARGE')
        return json.loads(raw)
    except ProbeRefusal: raise
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError):
        raise ProbeRefusal('PROVIDER_HTTP_OR_NETWORK_REFUSED') from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProbeRefusal('PROVIDER_NON_JSON_RESPONSE') from None


def probe(key: str, *, root: Path = ROOT, transport=request_json) -> dict:
    if not key.strip() or len(key) > 4096 or any(ord(x) < 33 or ord(x) > 126 for x in key):
        raise ProbeRefusal('NEXUS_KEY_REQUIRED_OR_INVALID')
    query = query_from_source(root)
    def variables(offset: int) -> dict:
        return {'filter': {'filter': [{'gameId': {'value': '1303', 'op': 'EQUALS'}}], 'op': 'AND'},
                'sort': [{'endorsements': {'direction': 'DESC'}}], 'offset': offset}
    first, count = validate_page(transport(GRAPHQL, key, {'query': query,
                                                         'variables': variables(0)}), 0)
    if not first: raise ProbeRefusal('PROVIDER_EMPTY_SAMPLE_NOT_QUALIFIED')
    pagination_checked = False
    if len(first) == 50 and count > 50:
        second, count2 = validate_page(transport(GRAPHQL, key, {
            'query': query, 'variables': variables(50)}), 50)
        if count2 < 50 or not second: raise ProbeRefusal('PROVIDER_SECOND_PAGE_UNVERIFIABLE')
        # Catalog contents change; don't claim stable ordering based on one request pair.
        pagination_checked = True
    mod_id = positive_id(first[0]['modId'])
    details = transport(REST+mod_id+'.json', key)
    if not isinstance(details, dict) or positive_id(details.get('mod_id')) != mod_id:
        raise ProbeRefusal('PROVIDER_DETAIL_ID_MISMATCH')
    files = transport(REST+mod_id+'/files.json', key)
    if not isinstance(files, dict) or not isinstance(files.get('files'), list):
        raise ProbeRefusal('PROVIDER_FILES_SHAPE_INVALID')
    if len(files['files']) > 2500:
        raise ProbeRefusal('PROVIDER_FILES_UNBOUNDED')
    # Public provider data, metadata, identities and API key are *never* copied to receipts.
    return {'result': 'NEX_R2C_AUTHENTICATED_LIVE_PROVIDER_PASS',
            'live_provider_verified': True, 'graphql_category_field_verified': True,
            'graphql_updated_at_field_verified': True,
            'provider_first_page_verified': True,
            'second_page_checked': pagination_checked,
            'provider_detail_verified': True, 'provider_files_endpoint_verified': True,
            'native_app_navigation_verified': False,
            'device_or_release_qualified': False,
            'account_details_included': False, 'raw_provider_payload_included': False}


def main() -> int:
    parser = argparse.ArgumentParser(description='Explicit Nexus API read-only live schema probe')
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    key = os.environ.get('CINDERBOX_NEXUS_API_KEY', '')
    try:
        result = probe(key)
        dest = args.receipt
        if dest.is_symlink() or dest.exists(): raise ProbeRefusal('RECEIPT_DESTINATION_ALREADY_EXISTS')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n', encoding='utf-8')
        print('NEX_R2C_AUTHENTICATED_LIVE_PROVIDER_PASS_RECEIPT_ONLY')
        return 0
    except ProbeRefusal as error:
        print('NEX_R2C_LIVE_REFUSED:'+str(error),file=sys.stderr)
        return 1
    except Exception:
        # Never print provider exceptions, traceback, header data or credential values.
        print('NEX_R2C_LIVE_REFUSED:UNEXPECTED_PROVIDER_FAILURE',file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
