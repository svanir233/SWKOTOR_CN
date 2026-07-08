#!/usr/bin/env python3
"""Generate KOTOR bitmap font TGA/TXI files from a TrueType/OpenType font.

The generated atlases intentionally place Chinese glyphs at both their Unicode
codepoints and their CP936 two-byte values. KOTOR Chinese rendering behavior is
not consistently documented, so this gives the Override font pack a better
chance of matching either path.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import struct
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont


FONT_SPECS = {
    "fnt_s10x10": 10,
    "fnt_galahad11": 11,
    "fnt_s14x14": 14,
    "fnt_galahad14": 14,
    "fnt_d16x16": 16,
    "fnt_d16x16b": 16,
    "fnt_s18x18": 18,
    "fnt_d24x24": 24,
}

ATLAS_WIDTH = 4096
RANGE_START = 0
RANGE_END = 0xFFFF
NUM_CHARS = RANGE_END - RANGE_START + 1


@dataclass(frozen=True)
class Glyph:
    char: str
    codes: tuple[int, ...]


def collect_glyphs(text_paths: list[pathlib.Path]) -> list[Glyph]:
    chars: set[str] = set()
    for path in text_paths:
        text = path.read_text(encoding="utf-8")
        chars.update(text)

    # Keep ASCII renderable even when the Override font shadows the stock font.
    chars.update(chr(i) for i in range(32, 127))
    chars.update("\t\r\n")

    glyphs: list[Glyph] = []
    used_codes: dict[int, str] = {}
    for char in sorted(chars, key=ord):
        codes = {ord(char)}
        try:
            raw = char.encode("cp936")
        except UnicodeEncodeError:
            raw = b""

        if len(raw) == 1:
            codes.add(raw[0])
        elif len(raw) == 2:
            codes.add((raw[0] << 8) | raw[1])

        valid_codes = []
        for code in sorted(codes):
            if RANGE_START <= code <= RANGE_END and code not in used_codes:
                valid_codes.append(code)
                used_codes[code] = char
        if valid_codes:
            glyphs.append(Glyph(char, tuple(valid_codes)))
    return glyphs


def tga_rle_packet(raw: bytes) -> bytes:
    out = bytearray()
    pixels = [raw[i : i + 4] for i in range(0, len(raw), 4)]
    i = 0
    while i < len(pixels):
        run = 1
        while i + run < len(pixels) and run < 128 and pixels[i + run] == pixels[i]:
            run += 1
        if run >= 2:
            out.append(0x80 | (run - 1))
            out.extend(pixels[i])
            i += run
            continue

        start = i
        i += 1
        while i < len(pixels):
            next_run = 1
            while i + next_run < len(pixels) and next_run < 128 and pixels[i + next_run] == pixels[i]:
                next_run += 1
            if next_run >= 2 or i - start >= 128:
                break
            i += 1

        count = i - start
        out.append(count - 1)
        for pixel in pixels[start:i]:
            out.extend(pixel)
    return bytes(out)


def write_tga_rgba(path: pathlib.Path, image: Image.Image) -> None:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    # TGA stores BGRA. Use top-left origin so UV coordinates match directly.
    bgra = bytearray()
    data = rgba.tobytes()
    for i in range(0, len(data), 4):
        r, g, b, a = data[i : i + 4]
        bgra.extend((b, g, r, a))

    header = bytearray(18)
    header[2] = 10  # RLE true-color image
    header[12:14] = struct.pack("<H", width)
    header[14:16] = struct.pack("<H", height)
    header[16] = 32
    header[17] = 0x28  # 8 alpha bits, top-left origin
    row_bytes = width * 4
    encoded = bytearray()
    for row_start in range(0, len(bgra), row_bytes):
        encoded.extend(tga_rle_packet(bytes(bgra[row_start : row_start + row_bytes])))
    path.write_bytes(bytes(header) + bytes(encoded) + b"\0" * 8 + b"TRUEVISION-XFILE.\0")


def uv_for_cell(code: int, columns: int, rows: int) -> tuple[float, float, float, float]:
    idx = code - RANGE_START
    col = idx % columns
    row = idx // columns
    x0 = col / columns
    y0 = 1 - (row / rows)
    x1 = (col + 1) / columns
    y1 = 1 - ((row + 1) / rows)
    return x0, y0, x1, y1


def write_txi(path: pathlib.Path, cell: int, columns: int, rows: int) -> None:
    lines = [
        "mipmap 0",
        "filter 0",
        f"numchars {NUM_CHARS}",
        f"rows {rows}",
        f"cols {columns}",
        "codepage 936",
        f"fontheight {cell / (rows * cell):.6f}",
        f"baselineheight {math.floor(cell * 0.82) / (rows * cell):.6f}",
        f"texturewidth {columns * cell / 100:.6f}",
        "fontwidth 1.000000",
        "spacingR 0.000000",
        f"spacingB {cell / (rows * cell):.6f}",
        "caretindent -0.010000",
        f"filerange {RANGE_START} {RANGE_END}",
        f"upperleftcoords {NUM_CHARS}",
    ]
    for code in range(RANGE_START, RANGE_END + 1):
        x0, y0, x1, y1 = uv_for_cell(code, columns, rows)
        lines.append(f"    {x0:.6f} {y0:.6f} 0")
    lines.append(f"lowerrightcoords {NUM_CHARS}")
    for code in range(RANGE_START, RANGE_END + 1):
        x0, y0, x1, y1 = uv_for_cell(code, columns, rows)
        lines.append(f"    {x1:.6f} {y1:.6f} 0")
    lines.append("")
    path.write_text("\n".join(lines), encoding="ascii")


def render_font(name: str, point_size: int, glyphs: list[Glyph], font_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    cell = point_size
    columns = ATLAS_WIDTH // cell
    rows = math.ceil(NUM_CHARS / columns)
    width = columns * cell
    height = rows * cell

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), point_size)

    for glyph in glyphs:
        bbox = draw.textbbox((0, 0), glyph.char, font=font, stroke_width=0)
        glyph_w = bbox[2] - bbox[0]
        glyph_h = bbox[3] - bbox[1]
        x_offset = max(0, (cell - glyph_w) // 2) - bbox[0]
        y_offset = max(0, (cell - glyph_h) // 2) - bbox[1]
        for code in glyph.codes:
            idx = code - RANGE_START
            col = idx % columns
            row = idx // columns
            x = col * cell + x_offset
            y = row * cell + y_offset
            draw.text((x, y), glyph.char, font=font, fill=(255, 255, 255, 255))

    write_tga_rgba(out_dir / f"{name}.tga", image)
    write_txi(out_dir / f"{name}.txi", cell, columns, rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", required=True, type=pathlib.Path)
    parser.add_argument("--out", default=pathlib.Path("fonts"), type=pathlib.Path)
    parser.add_argument("texts", nargs="+", type=pathlib.Path)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    glyphs = collect_glyphs(args.texts)
    for name, point_size in FONT_SPECS.items():
        render_font(name, point_size, glyphs, args.font, args.out)


if __name__ == "__main__":
    main()
