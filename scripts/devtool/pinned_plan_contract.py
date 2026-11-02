#!/usr/bin/env python3
"""Validate the exact Devtool 1.1.0 machine-wrapped plan response (no network).

Pinned A05/A07 `-m devtool ... plan --json` returns an envelope with
schema_version=1, machine.operation.status='ok', and a nested `data` payload
with schema_version=2. Never conflate the envelope with the plan itself.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys


def validate_receipt(receipt: object, action: str, lane: str) -> int:
    if not isinstance(receipt, dict):
        raise ValueError(f'INVALID_PINNED_DEVTOOL_ENVELOPE_{lane}')
    operation = receipt.get('machine', {}).get('operation', {}) if isinstance(receipt.get('machine'), dict) else {}
    data = receipt.get('data')
    if (receipt.get('schema_version') != 1 or not isinstance(operation, dict)
            or operation.get('status') != 'ok' or operation.get('command') != 'plan'
            or not isinstance(data, dict) or data.get('schema_version') != 2
            or data.get('action') != action or 'cinderbox' not in data.get('targets', [])
            or not isinstance(data.get('summary'), dict)
            or not isinstance(data['summary'].get('node_count'), int)
            or isinstance(data['summary'].get('node_count'), bool)
            or data['summary']['node_count'] < 1
            or not isinstance(data.get('commands'), list) or not data['commands']):
        raise ValueError(f'INVALID_PINNED_DEVTOOL_PLAN_{lane}')
    return data['summary']['node_count']


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print('usage: pinned_plan_contract.py RECEIPT_JSON WORKFLOW LANE', file=sys.stderr)
        return 2
    filename, workflow, lane = argv
    try:
        with Path(filename).open(encoding='utf-8') as source:
            receipt = json.load(source)
        nodes = validate_receipt(receipt, workflow, lane)
    except (OSError, ValueError) as exc:
        print(f'PINNED_DEVTOOL_PLAN_FAILURE: {exc}', file=sys.stderr)
        try:
            print(Path(filename).read_text(encoding='utf-8')[:16000], file=sys.stderr)
        except OSError:
            pass
        return 1
    print(f'PASS_PINNED_DEVTOOL_PLAN_{lane}: nodes={nodes}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
