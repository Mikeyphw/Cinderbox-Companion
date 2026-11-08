#!/usr/bin/env python3
"""NEX-R5 read-only, fail-closed Nexus Posts/Gallery capability probe.

No page scraping, no WebView, no writes/mutations, no mod comments or media bodies.
Only a bounded GraphQL schema introspection plus optional mod identity lookup.
A native feed is NOT qualified by a matching schema field alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = 'https://api.nexusmods.com/v2/graphql'
GRAPHQL_DOCS = 'https://graphql.nexusmods.com/'
GAME_ID = '1303'
MAX_HTTP_BYTES = 512_000
MAX_REPORT_BYTES = 16_384
TIMEOUT_SECONDS = 12
PROBE_VERSION = 1

# Only schema metadata is requested; never retrieve comments or third-party images.
SCHEMA_QUERY = '''query CinderboxCommunitySchemaV1 {
  root: __type(name: "Query") {
    fields {
      name
      args { name type { kind name ofType { kind name ofType { kind name } } } }
    }
  }
  mod: __type(name: "Mod") { fields { name } }
  mediaFilter: __type(name: "MediaSearchFilter") { inputFields { name } }
  commentThread: __type(name: "CommentThread") { fields { name } }
}'''

IDENTITY_QUERY = '''query CinderboxCommunityModIdentityV1($modId: ID!, $gameId: ID!) {
  mod(modId: $modId, gameId: $gameId) { modId gameId uid }
}'''

ROOT_POSTS_CANDIDATES = {'modcomments', 'modposts', 'postsformod', 'commentsformod', 'modcommentthread'}
ROOT_MEDIA_CANDIDATES = {'modmedia', 'modimages', 'modvideos', 'mediaformod', 'imagesformod', 'videosformod'}
MOD_POSTS_CANDIDATES = {'comments', 'commentthread', 'commentthreadid', 'posts', 'postthread'}
MOD_MEDIA_CANDIDATES = {'media', 'images', 'videos', 'gallery', 'galleryimages'}
MOD_SCOPE_ARGS = {'modid', 'moduid', 'legacymodid'}


def _names(items: object) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {entry['name'] for entry in items
            if isinstance(entry, dict) and isinstance(entry.get('name'), str)
            and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}', entry['name'])}


def _fields(node: object, key: str = 'fields') -> list[dict]:
    if not isinstance(node, dict) or not isinstance(node.get(key), list):
        return []
    return [entry for entry in node[key] if isinstance(entry, dict)]


def _root_scope_candidate(fields: list[dict], valid_names: set[str]) -> list[str]:
    result = []
    for field in fields:
        name = field.get('name')
        if not isinstance(name, str) or name.lower() not in {n.lower() for n in valid_names}:
            continue
        if {n.lower() for n in _names(field.get('args', []))} & MOD_SCOPE_ARGS:
            result.append(name)
    return sorted(set(result))


def assess_schema(envelope: dict, mod_id: str | None = None) -> dict:
    """Never infer a per-mod relation from a game/owner/text filter or thread ID."""
    if not isinstance(envelope, dict):
        raise ValueError('NON_OBJECT_GRAPHQL_ENVELOPE')
    if envelope.get('errors'):
        return unavailable('GRAPHQL_ERRORS')
    data = envelope.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('root'), dict) or not isinstance(data.get('mod'), dict):
        return unavailable('SCHEMA_INTROSPECTION_UNAVAILABLE')
    root = _fields(data['root'])
    mod_fields = _names(_fields(data['mod']))
    root_names = _names(root)
    media_filter = _names(_fields(data.get('mediaFilter'), 'inputFields'))
    thread_fields = _names(_fields(data.get('commentThread')))

    mod_posts = sorted(n for n in mod_fields if n.lower() in MOD_POSTS_CANDIDATES)
    root_posts = _root_scope_candidate(root, ROOT_POSTS_CANDIDATES)
    mod_media = sorted(n for n in mod_fields if n.lower() in MOD_MEDIA_CANDIDATES)
    root_media = _root_scope_candidate(root, ROOT_MEDIA_CANDIDATES)
    media_scope = sorted(n for n in media_filter if n.lower() in MOD_SCOPE_ARGS)

    # Never misidentify commentThread(commentThreadId) as a mod-scoped operation.
    posts_candidate = bool(mod_posts or root_posts)
    media_candidate = bool(mod_media or root_media or ('media' in root_names and media_scope))
    report = {
        'probe_version': PROBE_VERSION,
        'endpoint': ENDPOINT,
        'source': GRAPHQL_DOCS,
        'game_id': GAME_ID,
        'mod_id': mod_id,
        'schema_status': 'READ',
        'schema_fingerprint': hashlib.sha256(json.dumps({
            'root': sorted(root_names), 'mod': sorted(mod_fields),
            'mediaFilter': sorted(media_filter), 'commentThread': sorted(thread_fields),
        }, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'posts': {
            'thread_by_id_available': 'commentThread' in root_names,
            'mod_fields': mod_posts,
            'mod_scoped_root_fields': root_posts,
            'candidate_found': posts_candidate,
            'native_state': 'CANDIDATE_REQUIRES_REAL_MOD_ATTRIBUTION'
                if posts_candidate else 'NO_VERIFIED_MOD_RELATION',
        },
        'media': {
            'site_wide_search_available': 'media' in root_names,
            'mod_fields': mod_media,
            'mod_scoped_root_fields': root_media,
            'mod_scoped_filter_fields': media_scope,
            'candidate_found': media_candidate,
            'native_state': 'CANDIDATE_REQUIRES_REAL_MOD_ATTRIBUTION'
                if media_candidate else 'NO_VERIFIED_MOD_RELATION',
        },
        'identity_lookup': 'NOT_RUN',
        'native_qualified': False,
        'personal_or_media_content_fetched': False,
        'credential_logged': False,
        'status': 'CANDIDATES_UNVERIFIED' if posts_candidate or media_candidate else 'NO_MOD_SCOPED_CONTRACT',
    }
    return report


def unavailable(reason: str) -> dict:
    return {
        'probe_version': PROBE_VERSION,
        'endpoint': ENDPOINT,
        'source': GRAPHQL_DOCS,
        'game_id': GAME_ID,
        'schema_status': 'UNAVAILABLE',
        'reason_code': reason,
        'posts': {'native_state': 'NOT_QUALIFIED'},
        'media': {'native_state': 'NOT_QUALIFIED'},
        'identity_lookup': 'NOT_RUN',
        'native_qualified': False,
        'personal_or_media_content_fetched': False,
        'credential_logged': False,
        'status': 'INCONCLUSIVE',
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def query_api(query: str, variables: dict | None = None) -> dict:
    if query not in (SCHEMA_QUERY, IDENTITY_QUERY):
        raise ValueError('UNAPPROVED_GRAPHQL_QUERY')
    payload = json.dumps({'query': query, 'variables': variables or {}},
                         separators=(',', ':')).encode('utf-8')
    # Never log request/response bodies, URLs other than the fixed endpoint, or API keys.
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Application-Name': 'Cinderbox Companion',
        'Application-Version': '0.1.1-nex-r5-probe',
    }
    key = os.environ.get('NEXUS_API_KEY', '').strip()
    if key:
        headers['apikey'] = key
    request = urllib.request.Request(ENDPOINT, payload, headers, method='POST')
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        length = response.read(MAX_HTTP_BYTES + 1)
    if len(length) > MAX_HTTP_BYTES:
        raise ValueError('RESPONSE_TOO_LARGE')
    data = json.loads(length.decode('utf-8'))
    if not isinstance(data, dict):
        raise ValueError('NON_OBJECT_RESPONSE')
    return data


def probe_live(mod_id: str | None) -> dict:
    try:
        report = assess_schema(query_api(SCHEMA_QUERY), mod_id)
    except urllib.error.HTTPError as e:
        return unavailable('HTTP_' + str(e.code) if e.code in (400, 401, 403, 404, 408, 429, 500, 502, 503, 504)
                           else 'HTTP_ERROR')
    except (urllib.error.URLError, OSError, TimeoutError):
        return unavailable('TRANSPORT_UNAVAILABLE')
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return unavailable('INVALID_SCHEMA_RESPONSE')
    if mod_id is not None and report['schema_status'] == 'READ':
        # Identity-only; DOES NOT fetch any images, posts or user-generated text.
        try:
            result = query_api(IDENTITY_QUERY, {'modId': mod_id, 'gameId': GAME_ID})
            mod = (result.get('data') or {}).get('mod')
            if isinstance(mod, dict) and str(mod.get('modId')) == mod_id and str(mod.get('gameId')) == GAME_ID:
                report['identity_lookup'] = 'MATCHED'
            else:
                report['identity_lookup'] = 'UNAVAILABLE_OR_MISMATCH'
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError, ValueError, UnicodeError):
            report['identity_lookup'] = 'UNAVAILABLE'
    return report


def write_receipt(destination: str, report: dict) -> None:
    path = Path(destination).expanduser()
    if path.is_symlink():
        raise ValueError('OUTPUT_SYMLINK_REFUSED')
    payload = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode('utf-8')
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError('REPORT_TOO_LARGE')
    # O_EXCL, mode 0600: never overwrite or follow links from previous runs.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--live', action='store_true', help='Bounded read-only GraphQL calls')
    source.add_argument('--fixture', type=Path, help='Offline schema fixture (no HTTP)')
    parser.add_argument('--mod-id', help='Numeric Stardew Valley mod ID, identity lookup only')
    parser.add_argument('--output', help='New 0600 sanitized receipt file (refuses overwrite)')
    args = parser.parse_args(argv)
    if args.mod_id is not None and not re.fullmatch(r'[1-9][0-9]{0,11}', args.mod_id):
        parser.error('mod-id must be a positive numeric ID')
    if args.fixture:
        try:
            if args.fixture.stat().st_size > MAX_HTTP_BYTES:
                raise ValueError('FIXTURE_TOO_LARGE')
            report = assess_schema(json.loads(args.fixture.read_text(encoding='utf-8')), args.mod_id)
        except (OSError, UnicodeError, ValueError) as exc:
            # No untrusted contents/errors in logs.
            print('NEX_R5_PROBE_REFUSED_INVALID_FIXTURE', file=sys.stderr)
            return 2
    else:
        report = probe_live(args.mod_id)
    if args.output:
        try:
            write_receipt(args.output, report)
        except (OSError, ValueError):
            print('NEX_R5_PROBE_REFUSED_OUTPUT', file=sys.stderr)
            return 2
    # Only a compact receipt is emitted, no raw provider output or credentials.
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    if report['status'] in ('INCONCLUSIVE', 'NO_MOD_SCOPED_CONTRACT'):
        print('NEX_R5_NATIVE_COMMUNITY_NOT_QUALIFIED_BROWSER_FALLBACK_ACTIVE')
    else:
        print('NEX_R5_COMMUNITY_SCHEMA_CANDIDATE_ONLY_REAL_MOD_VALIDATION_REQUIRED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
