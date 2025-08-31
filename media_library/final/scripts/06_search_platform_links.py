#!/usr/bin/env python3
"""
Search entries in platform_links.csv based on query terms.

Rules (from README_02.md):
- Accept comma-separated search terms; terms are in an ANY relationship.
- Search in fields: tags and title.
- Sort results by platform (ascending) and then pubdate (ascending).
- Support searching across multiple CSV files at once.
- Output only these fields: link_id, platform, share_url, title, pubdate,
  cover_url, tags, co_operators, author, related_series, path (source CSV path).
- Output format: JSON (UTF-8, keep Chinese characters).
- Default input path: data/test_02/platform_links.csv
- Multiple inputs are comma-separated via --input "path1,path2"
- Default output directory: test_output/test_02
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict, Any


CSV_REQUIRED_FIELDS = [
    "link_id",
    "platform",
    "share_url",
    "title",
    "pubdate",
    "cover_url",
    "tags",
    "co_operators",
    "author",
    "related_series",
]

# Output fields include an extra synthetic field 'path' indicating the source CSV file path.
OUTPUT_FIELDS = CSV_REQUIRED_FIELDS + ["path"]


@dataclass
class SearchConfig:
    input_csv_paths: List[Path]
    output_json_path: Path
    search_terms: List[str]


def parse_args() -> SearchConfig:
    project_root = Path(__file__).resolve().parents[1]
    default_input = project_root / "data/test_02/platform_links.csv"
    default_output_dir = project_root / "test_output/test_02"
    default_output = default_output_dir / "search_results.json"

    parser = argparse.ArgumentParser(
        description="Search platform_links.csv by title/tags and output JSON results.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Comma-separated search terms. ANY match across title or tags will be included.",
    )
    parser.add_argument(
        "--input",
        default=str(default_input),
        help=(
            "Comma-separated input CSV paths. Example: --input 'a.csv,b.csv'. "
            f"Default: {default_input}"
        ),
    )
    parser.add_argument(
        "--output",
        default=str(default_output),
        help=f"Path to output JSON. Default: {default_output}",
    )

    args = parser.parse_args()

    search_terms = [term.strip().lower() for term in args.query.split(",") if term.strip()]
    if not search_terms:
        raise SystemExit("No valid search terms provided. Use --query 'term1,term2'.")

    input_paths = [Path(p.strip()) for p in str(args.input).split(",") if str(p).strip()]

    return SearchConfig(
        input_csv_paths=input_paths,
        output_json_path=Path(args.output),
        search_terms=search_terms,
    )


def ensure_required_fields_exist(row: Dict[str, Any]) -> None:
    missing = [field for field in CSV_REQUIRED_FIELDS if field not in row]
    if missing:
        raise ValueError(f"CSV is missing required fields: {missing}")


def parse_pubdate(value: str) -> datetime:
    # Expected format: YYYY/MM/DD
    try:
        return datetime.strptime(value.strip(), "%Y/%m/%d")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid pubdate format: {value!r}; expected YYYY/MM/DD") from exc


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def row_matches_any_term(row: Dict[str, Any], search_terms: Iterable[str]) -> bool:
    title = normalize_text(row.get("title", "")).lower()
    tags = normalize_text(row.get("tags", "")).lower()
    for term in search_terms:
        if not term:
            continue
        if term in title or term in tags:
            return True
    return False


def filter_and_sort_rows(rows: List[Dict[str, Any]], search_terms: List[str]) -> List[Dict[str, Any]]:
    matching_rows: List[Dict[str, Any]] = []
    for row in rows:
        ensure_required_fields_exist(row)
        if row_matches_any_term(row, search_terms):
            matching_rows.append(row)

    def sort_key(r: Dict[str, Any]):
        platform = normalize_text(r.get("platform", ""))
        pubdate = parse_pubdate(normalize_text(r.get("pubdate", "")))
        return (platform, pubdate)

    matching_rows.sort(key=sort_key)
    return matching_rows


def project_fields(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    projected: List[Dict[str, Any]] = []
    for row in rows:
        projected.append({field: normalize_text(row.get(field, "")) for field in OUTPUT_FIELDS})
    return projected


def read_csv_rows(csv_path: Path) -> List[Dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")
    # Use utf-8-sig to strip BOM if present and normalize header names
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        normalized_rows: List[Dict[str, Any]] = []
        for row in reader:
            # Remove BOM from any header key if present
            normalized = { (k.lstrip("\ufeff") if isinstance(k, str) else k): v for k, v in row.items() }
            normalized_rows.append(normalized)
        return normalized_rows


def read_csv_rows_from_paths(csv_paths: List[Path]) -> List[Dict[str, Any]]:
    combined: List[Dict[str, Any]] = []
    for path in csv_paths:
        for row in read_csv_rows(path):
            enriched = dict(row)
            enriched["path"] = str(path)
            combined.append(enriched)
    return combined


def write_json(output_path: Path, data: Any) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    config = parse_args()
    rows = read_csv_rows_from_paths(config.input_csv_paths)
    filtered_sorted_rows = filter_and_sort_rows(rows, config.search_terms)
    result_rows = project_fields(filtered_sorted_rows)
    write_json(config.output_json_path, result_rows)
    print(
        f"Wrote {len(result_rows)} results to {config.output_json_path} \n"
        f"Terms: {', '.join(config.search_terms)}\n"
        f"Input: {', '.join(str(p) for p in config.input_csv_paths)}"
    )


if __name__ == "__main__":
    main()