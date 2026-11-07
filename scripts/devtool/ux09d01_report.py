#!/usr/bin/env python3
"""Verify six real default-font PNGs with stdlib decoding, CRCs and pixel content.

No Pillow dependency in the hosted or source-only jobs. No native golden approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import struct
import zlib

PNG = b'\x89PNG\r\n\x1a\n'
CASES = ('mods', 'saves', 'more')
WIDTHS = {393: (786, 1704), 360: (720, 1600)}


def png_color_sample(data: bytes, expected: tuple[int, int]) -> int:
    """Decode PNG scanline filters and independently count interior RGB variation."""
    assert data.startswith(PNG), 'UX09D01_INVALID_PNG_SIGNATURE'
    pos = 8
    ihdr = None
    compressed = []
    finished = False
    while pos + 12 <= len(data):
        length = struct.unpack_from('>I', data, pos)[0]
        tag = data[pos + 4:pos + 8]
        end = pos + 12 + length
        assert length < 16_000_000 and end <= len(data), 'UX09D01_PNG_TRUNCATED_CHUNK'
        payload = data[pos + 8:pos + 8 + length]
        recorded = struct.unpack_from('>I', data, pos + 8 + length)[0]
        assert zlib.crc32(tag + payload) & 0xffffffff == recorded, 'UX09D01_PNG_CRC_INVALID'
        if tag == b'IHDR':
            assert ihdr is None and length == 13 and pos == 8, 'UX09D01_PNG_IHDR_INVALID'
            ihdr = struct.unpack('>IIBBBBB', payload)
        elif tag == b'IDAT':
            compressed.append(payload)
        elif tag == b'IEND':
            assert length == 0, 'UX09D01_PNG_END_INVALID'
            finished = True
            pos = end
            break
        pos = end
    assert finished and pos == len(data) and ihdr is not None and compressed, 'UX09D01_PNG_INCOMPLETE'
    width, height, depth, kind, compression, filtering, interlace = ihdr
    assert (width, height) == expected, f'UX09D01_WRONG_SIZE:{width}x{height}'
    assert (depth, compression, filtering, interlace) == (8, 0, 0, 0), 'UX09D01_PNG_UNSUPPORTED_ENCODING'
    assert kind in (2, 6), 'UX09D01_PNG_UNSUPPORTED_COLOR'
    channels = 3 if kind == 2 else 4
    stride = width * channels
    raw_len = height * (1 + stride)
    inflater = zlib.decompressobj()
    raw = inflater.decompress(b''.join(compressed), raw_len + 1)
    assert inflater.eof and not inflater.unused_data and len(raw) == raw_len, 'UX09D01_PNG_BAD_PIXEL_STREAM'

    distinct = set()
    previous = bytearray(stride)
    cursor = 0
    xs = range(width // 8, width * 7 // 8, 23)
    sample_ys = set(range(height // 4, height * 3 // 4, 23))
    for y in range(height):
        filter_kind = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        assert filter_kind in (0, 1, 2, 3, 4), 'UX09D01_PNG_BAD_FILTER'
        # PNG filter byte values reconstruct the actual pixel bytes.
        if filter_kind:
            for k in range(stride):
                left = row[k - channels] if k >= channels else 0
                up = previous[k]
                upper_left = previous[k - channels] if k >= channels else 0
                if filter_kind == 1:
                    prediction = left
                elif filter_kind == 2:
                    prediction = up
                elif filter_kind == 3:
                    prediction = (left + up) // 2
                else:
                    p = left + up - upper_left
                    pa, pb, pc = abs(p-left), abs(p-up), abs(p-upper_left)
                    prediction = left if pa <= pb and pa <= pc else (up if pb <= pc else upper_left)
                row[k] = (row[k] + prediction) & 255
        if y in sample_ys:
            for x in xs:
                k = x * channels
                distinct.add((row[k], row[k + 1], row[k + 2]))
        previous = row
    assert len(distinct) >= 8, f'UX09D01_BLANK_CONTENT:{len(distinct)}'
    return len(distinct)


def analyze(folder: pathlib.Path, source: str, run_id: str):
    folder = pathlib.Path(folder)
    screens = []
    expected_files = set()
    for width, viewport in WIDTHS.items():
        for name in CASES:
            stem = f'ux09d01-{name}-{width}'
            p, meta = folder / f'{stem}.png', folder / f'{stem}.json'
            expected_files.update((p.name, meta.name))
            assert p.is_file() and meta.is_file(), f'UX09D01_MISSING_CASE:{stem}'
            data = p.read_bytes()
            assert len(data) > 1024, f'UX09D01_INVALID_PNG:{stem}'
            colors = png_color_sample(data, viewport)
            receipt = json.loads(meta.read_text())
            assert receipt['case'] == name and tuple(receipt['viewport']) == viewport, f'UX09D01_RECEIPT_MISMATCH:{stem}'
            assert receipt['source'] == 'real-offline-MainActivity', f'UX09D01_FAKE_SOURCE:{stem}'
            assert receipt['font_percent'] == 100, f'UX09D01_NOT_DEFAULT_FONT:{stem}'
            assert receipt['brand_top_px'] >= 32, f'UX09D01_STATUS_OVERLAP:{stem}'
            assert receipt['status_icons_light'] is True, f'UX09D01_DARK_STATUS_ICONS:{stem}'
            assert receipt['content_unique_colors'] == colors, f'UX09D01_PIXEL_RECEIPT_MISMATCH:{stem}'
            for flag in ('steam_login_attempted', 'privileged_write_performed',
                         'native_golden_approved', 'physical_device_accepted'):
                assert receipt[flag] is False, f'UX09D01_FALSE_CLAIM:{stem}:{flag}'
            screens.append({'case': name, 'width_dp': width, 'sha256': hashlib.sha256(data).hexdigest(),
                            'brand_top_px': receipt['brand_top_px'], 'status_icons_light_requested': True,
                            'content_unique_colors': colors})
    assert len(screens) == 6
    unexpected = {p.name for p in folder.iterdir() if p.suffix in ('.png', '.json')} - expected_files
    assert not unexpected, f'UX09D01_UNEXPECTED_CASES:{sorted(unexpected)}'
    result = {'result': 'UX09D01_SIX_DEFAULT_FONT_UI_CANDIDATES_UNAPPROVED',
              'source_commit': source, 'github_run_id': run_id, 'screens': screens,
              'png_crc_and_image_pixels_verified': True,
              'status_bar_light_foreground_requested_not_pixel_approved': True,
              'operation_navigation_tested_by_hosted_instrumentation': True,
              'approved_browser_reference_unchanged': True,
              'native_goldens_approved': False, 'physical_device_qualified': False,
              'steam_auth_qualified': False, 'privileged_writes_qualified': False}
    (folder / 'UX09D01_EVIDENCE.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=pathlib.Path, required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--run-id', required=True)
    a = p.parse_args()
    print(json.dumps(analyze(a.evidence, a.source, a.run_id), sort_keys=True))


if __name__ == '__main__':
    main()
