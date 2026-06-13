#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"a": MAIN_NS, "r": REL_NS, "pr": PKG_REL_NS}

FIELD_ALIASES = {
    "producer": {"producer", "producername", "estate", "winery"},
    "wine": {"wine", "winename", "cuvee"},
    "vintage": {"vintage", "year", "vintageyear"},
    "country": {"country"},
    "region": {"region"},
    "sub_region": {"subregion", "sub-region"},
    "style": {"style", "type"},
    "status": {"status"},
    "channel": {"channel"},
    "quantity": {"quantity", "qty"},
}
HEADER_HINTS = {item for values in FIELD_ALIASES.values() for item in values}
DISTRIBUTION_FIELDS = ("country", "region", "sub_region", "style", "status", "channel", "vintage")


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha()).upper()
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for string_item in root.findall("a:si", NS):
        parts = [node.text or "" for node in string_item.iter(f"{{{MAIN_NS}}}t")]
        values.append("".join(parts))
    return values


def cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t")).strip()

    value_node = cell.find("a:v", NS)
    if value_node is None or value_node.text is None:
        return ""

    raw_value = value_node.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)].strip()
        except (IndexError, ValueError):
            return raw_value
    if cell_type == "b":
        return "TRUE" if raw_value == "1" else "FALSE"
    return raw_value


def workbook_sheets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("pr:Relationship", NS)
        if rel.attrib.get("Type", "").endswith("/worksheet")
    }

    sheets: list[tuple[str, str]] = []
    sheets_node = workbook.find("a:sheets", NS)
    if sheets_node is None:
        return sheets

    for sheet in sheets_node:
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = rel_map.get(rel_id)
        if target:
            sheets.append((name, f"xl/{target}"))
    return sheets


def parse_sheet_rows(archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> list[dict[int, str]]:
    root = ET.fromstring(archive.read(sheet_path))
    rows: list[dict[int, str]] = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        parsed: dict[int, str] = {}
        for cell in row.findall("a:c", NS):
            parsed[column_index(cell.attrib.get("r", "A1"))] = cell_text(cell, shared_strings)
        rows.append(parsed)
    return rows


def row_score(row_values: Iterable[str]) -> tuple[int, int]:
    non_empty = [value.strip() for value in row_values if value and value.strip()]
    keyword_hits = sum(1 for value in non_empty if normalize_header(value) in HEADER_HINTS)
    return keyword_hits, len(non_empty)


def detect_header_row(rows: list[dict[int, str]]) -> int | None:
    if not rows:
        return None

    limit = min(len(rows), 10)
    candidates = [(index, row_score(rows[index].values())) for index in range(limit)]
    best_index, best_score = max(candidates, key=lambda item: item[1])
    if best_score == (0, 0):
        return None
    return best_index


def build_headers(rows: list[dict[int, str]], header_row_index: int) -> list[str]:
    max_col = max((max(row.keys()) for row in rows if row), default=-1)
    header_row = rows[header_row_index]
    headers: list[str] = []
    seen: Counter[str] = Counter()

    for index in range(max_col + 1):
        base = header_row.get(index, "").strip() or f"column_{index + 1}"
        seen[base] += 1
        if seen[base] > 1:
            base = f"{base}_{index + 1}"
        headers.append(base)
    return headers


def rows_to_records(rows: list[dict[int, str]], header_row_index: int, headers: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for row in rows[header_row_index + 1 :]:
        record = {header: row.get(index, "").strip() for index, header in enumerate(headers)}
        if any(value for value in record.values()):
            records.append(record)
    return records


def find_field_column(headers: list[str], field_name: str) -> str | None:
    aliases = FIELD_ALIASES[field_name]
    for header in headers:
        if normalize_header(header) in aliases:
            return header
    return None


def format_counter(counter: Counter[str], limit: int = 5) -> str:
    if not counter:
        return "none"
    parts = [f"{key}={value}" for key, value in counter.most_common(limit)]
    return ", ".join(parts)


def profile_sheet(sheet_name: str, records: list[dict[str, str]], headers: list[str], header_row_index: int | None) -> None:
    print(f"Sheet: {sheet_name}")
    print(f"  Header row: {header_row_index + 1 if header_row_index is not None else 'not found'}")
    print(f"  Columns ({len(headers)}): {', '.join(headers) if headers else 'none'}")
    print(f"  Row count: {len(records)}")

    if not headers:
        print("  Null counts: none")
        print("  Unique counts: producer=0, wine=0, vintage=0")
        print("  Distributions: none")
        print()
        return

    null_counts = {header: sum(1 for record in records if not record.get(header, "")) for header in headers}
    print("  Null counts:")
    for header, count in null_counts.items():
        print(f"    - {header}: {count}")

    producer_header = find_field_column(headers, "producer")
    wine_header = find_field_column(headers, "wine")
    vintage_header = find_field_column(headers, "vintage")
    producer_count = len({record[producer_header] for record in records if producer_header and record.get(producer_header)}) if producer_header else 0
    wine_count = len({record[wine_header] for record in records if wine_header and record.get(wine_header)}) if wine_header else 0
    vintage_count = len({record[vintage_header] for record in records if vintage_header and record.get(vintage_header)}) if vintage_header else 0
    print(f"  Unique counts: producer={producer_count}, wine={wine_count}, vintage={vintage_count}")

    print("  Distributions:")
    emitted = False
    for field_name in DISTRIBUTION_FIELDS:
        column = find_field_column(headers, field_name)
        if not column:
            continue
        counter = Counter(record[column] for record in records if record.get(column))
        print(f"    - {column}: {format_counter(counter)}")
        emitted = True
    if not emitted:
        print("    - none")

    warnings: list[str] = []
    if any(header.startswith("column_") for header in headers):
        warnings.append("contains blank fallback headers")
    if not records:
        warnings.append("contains no data rows")
    if not producer_header or not wine_header or not vintage_header:
        warnings.append("missing one or more producer/wine/vintage columns")
    if warnings:
        print(f"  Warnings: {', '.join(warnings)}")
    print()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Profile the sample WineList.xlsx workbook without external dependencies.")
    parser.add_argument(
        "workbook",
        nargs="?",
        default="data/sample/WineList.xlsx",
        help="Path to the xlsx workbook to inspect. Defaults to data/sample/WineList.xlsx.",
    )
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    if not workbook_path.is_file():
        print(f"Workbook not found: {workbook_path}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(workbook_path) as archive:
        shared_strings = read_shared_strings(archive)
        sheets = workbook_sheets(archive)

        print(f"Workbook: {workbook_path}")
        print(f"Sheet names ({len(sheets)}): {', '.join(name for name, _ in sheets)}")
        print()

        for sheet_name, sheet_path in sheets:
            rows = parse_sheet_rows(archive, sheet_path, shared_strings)
            header_row_index = detect_header_row(rows)
            headers = build_headers(rows, header_row_index) if header_row_index is not None else []
            records = rows_to_records(rows, header_row_index, headers) if header_row_index is not None else []
            profile_sheet(sheet_name, records, headers, header_row_index)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
