#!/usr/bin/env python3
"""Build a KOTOR dialog.tlk file from the translated text export."""

from __future__ import annotations

import argparse
import pathlib
import re
import struct


ENTRY_RE = re.compile(r"^(\d+)\s*:=\s?(.*)$")
HEADER_SIZE = 20
ENTRY_SIZE = 40


def parse_entries(path: pathlib.Path) -> dict[int, str]:
    entries: dict[int, list[str]] = {}
    current: int | None = None

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        if raw_line.startswith("#//"):
            continue

        match = ENTRY_RE.match(raw_line)
        if match:
            current = int(match.group(1))
            entries[current] = [match.group(2)]
            continue

        if current is not None:
            entries[current].append(raw_line)

    return {strref: "\n".join(lines) for strref, lines in entries.items()}


def encode_text(text: str, encoding: str) -> bytes:
    return text.encode(encoding)


def build_tlk(entries: dict[int, str], output: pathlib.Path, language_id: int, encoding: str, count: int | None) -> None:
    if not entries:
        raise ValueError("no TLK entries found")

    total = count if count is not None else max(entries) + 1
    if total <= max(entries):
        raise ValueError(f"entry count {total} is smaller than max StrRef {max(entries)}")

    string_data = bytearray()
    table = bytearray()

    for strref in range(total):
        text = entries.get(strref, "")
        encoded = encode_text(text, encoding) if text else b""
        offset = len(string_data)
        string_data.extend(encoded)

        flags = 1 if encoded else 0
        sound_resref = b"\0" * 16
        table.extend(
            struct.pack(
                "<I16sffIIf",
                flags,
                sound_resref,
                0.0,
                0.0,
                offset,
                len(encoded),
                0.0,
            )
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    data_offset = HEADER_SIZE + ENTRY_SIZE * total
    header = b"TLK V3.0" + struct.pack("<III", language_id, total, data_offset)
    output.write_bytes(header + table + string_data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--language-id", type=int, default=130)
    parser.add_argument("--encoding", default="cp936")
    parser.add_argument("--count", type=int)
    args = parser.parse_args()

    entries = parse_entries(args.input)
    build_tlk(entries, args.output, args.language_id, args.encoding, args.count)
    print(f"wrote {args.output} with {args.count or max(entries) + 1} entries")


if __name__ == "__main__":
    main()
